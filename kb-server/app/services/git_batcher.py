"""Debounced batcher that collects API note writes, commits to a daily branch, and creates a PR.

Usage
-----
Call ``enqueue(path)`` after each successful API write. A background
thread waits for the configured debounce window, then:
1. Checks out (or creates) a daily feature branch
2. Commits all queued changes (including deletions)
3. Pushes the branch to remote
4. Creates or updates a PR targeting the main branch

The batcher is a singleton - import and use the module-level ``batcher``
instance.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone

from app.core.config import settings
from app.models.db import Job, SessionLocal, VaultEvent
from app.services import git_service, github_service

log = logging.getLogger(__name__)


def _daily_branch_name() -> str:
    """Generate today's branch name, e.g., kb-api/2026-03-05."""
    prefix = settings.git_batch_branch_prefix
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"{prefix}/{date_str}"


class GitBatcher:
    def __init__(self, debounce_seconds: int | None = None):
        self.debounce_seconds = (
            debounce_seconds
            if debounce_seconds is not None
            else settings.git_batch_debounce_seconds
        )
        self._pending: set[str] = set()
        self._lock = threading.Lock()
        self._timer: threading.Timer | None = None

    def enqueue(self, path: str) -> None:
        """Add *path* to the current batch and reset the debounce timer."""
        with self._lock:
            self._pending.add(path)
            self._reset_timer()

    def _reset_timer(self) -> None:
        if self._timer is not None:
            self._timer.cancel()
        self._timer = threading.Timer(self.debounce_seconds, self._flush)
        self._timer.daemon = True
        self._timer.start()

    def _flush(self) -> None:
        with self._lock:
            if not self._pending:
                return
            files = sorted(self._pending)
            self._pending.clear()

        self._do_commit_and_pr(files)

    def _do_commit_and_pr(self, files: list[str]) -> None:
        session = SessionLocal()
        branch_name = _daily_branch_name()
        original_branch = None

        try:
            job = Job(
                job_type="git_batch",
                status="running",
                meta={"files": files, "branch": branch_name},
            )
            session.add(job)
            session.commit()

            original_branch = git_service.current_branch()
            git_service.checkout_or_create_from_main(branch_name)

            sha = git_service.commit_for_batch(files)
            if sha is None:
                job.status = "skipped"
                job.completed_at = datetime.now(timezone.utc)
                session.commit()
                log.info("git batch skipped - nothing to commit")
                return

            session.add(
                VaultEvent(
                    event_type="git_commit",
                    commit_sha=sha,
                    details={"files": files, "branch": branch_name},
                )
            )
            session.commit()

            try:
                git_service.push_branch(branch_name)
            except git_service.GitError as exc:
                log.error("git push failed: %s", exc)
                session.add(
                    VaultEvent(
                        event_type="git_push_failed",
                        commit_sha=sha,
                        details={"error": str(exc)[:2000], "branch": branch_name},
                    )
                )
                job.status = "failed"
                job.error = str(exc)[:2000]
                job.completed_at = datetime.now(timezone.utc)
                session.commit()
                return

            session.add(
                VaultEvent(
                    event_type="git_push",
                    commit_sha=sha,
                    details={"files": files, "branch": branch_name},
                )
            )
            session.commit()

            pr_url = None
            try:
                date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                pr_title = f"KB API updates ({date_str})"
                pr_body = f"Automated PR for API writes on {date_str}.\n\nFiles updated:\n"
                pr_body += "\n".join(f"- `{f}`" for f in files[:20])
                if len(files) > 20:
                    pr_body += f"\n- ... and {len(files) - 20} more"

                pr = github_service.ensure_pr(
                    head_branch=branch_name,
                    title=pr_title,
                    body=pr_body,
                )
                pr_url = pr.get("html_url")
                pr_number = pr.get("number")

                session.add(
                    VaultEvent(
                        event_type="pr_created",
                        commit_sha=sha,
                        details={
                            "branch": branch_name,
                            "pr_number": pr_number,
                            "pr_url": pr_url,
                        },
                    )
                )
                log.info("PR ready: %s", pr_url)

            except github_service.GitHubError as exc:
                log.warning("PR creation failed (branch pushed successfully): %s", exc)
                session.add(
                    VaultEvent(
                        event_type="pr_creation_failed",
                        commit_sha=sha,
                        details={"error": str(exc)[:2000], "branch": branch_name},
                    )
                )

            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc)
            session.commit()
            log.info(
                "git batch complete: branch=%s sha=%s (%d files)",
                branch_name,
                sha[:10],
                len(files),
            )

        except Exception:
            import traceback

            job.status = "failed"
            job.error = traceback.format_exc()[-2000:]
            job.completed_at = datetime.now(timezone.utc)
            session.commit()
            log.exception("git batch failed")
        finally:
            if original_branch and original_branch != branch_name:
                try:
                    git_service.checkout(original_branch)
                except Exception:
                    log.warning("Failed to return to original branch %s", original_branch)
            session.close()


batcher = GitBatcher()
