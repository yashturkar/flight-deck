"""File-watcher process that debounces vault changes and auto-commits.

Run as a standalone process::

    python -m app.workers.autosave
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path

from watchfiles import Change, awatch

from app.core.config import settings
from app.core.logging import setup_logging
from app.models.db import Job, SessionLocal, VaultEvent
from app.services import git_service, publish_service

log = logging.getLogger(__name__)


class AutosaveWatcher:
    """Watch the vault directory, debounce, then commit+push."""

    def __init__(
        self,
        vault_path: Path | None = None,
        debounce_seconds: int | None = None,
    ):
        self.vault_path = (vault_path or settings.vault_path).resolve()
        self.debounce_seconds = (
            debounce_seconds
            if debounce_seconds is not None
            else settings.autosave_debounce_seconds
        )
        self._pending: set[str] = set()
        self._flush_task: asyncio.Task | None = None

    async def run(self) -> None:
        log.info(
            "watching %s (debounce=%ds)",
            self.vault_path,
            self.debounce_seconds,
        )
        async for changes in awatch(
            self.vault_path,
            watch_filter=self._filter,
        ):
            for _change_type, path_str in changes:
                rel = str(Path(path_str).relative_to(self.vault_path))
                self._pending.add(rel)

            self._reset_timer()

    def _filter(self, change: Change, path: str) -> bool:
        """Ignore .git and other non-content paths."""
        p = Path(path)
        if ".git" in p.parts:
            return False
        return p.suffix.lower() in {".md", ".markdown", ".txt"}

    def _reset_timer(self) -> None:
        if self._flush_task and not self._flush_task.done():
            self._flush_task.cancel()
        self._flush_task = asyncio.create_task(self._debounce_then_flush())

    async def _debounce_then_flush(self) -> None:
        try:
            await asyncio.sleep(self.debounce_seconds)
        except asyncio.CancelledError:
            return

        if not self._pending:
            return

        files = set(self._pending)
        self._pending.clear()
        await asyncio.to_thread(self._do_autosave, files)

    def _do_autosave(self, files: set[str]) -> None:
        session = SessionLocal()
        try:
            job = Job(job_type="autosave", status="running", meta={"files": sorted(files)})
            session.add(job)
            session.commit()

            now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
            message = f"autosave: {now}"

            sha = git_service.commit(message)
            if sha is None:
                job.status = "skipped"
                job.completed_at = datetime.now(timezone.utc)
                session.commit()
                return

            session.add(
                VaultEvent(
                    event_type="autosave_commit",
                    commit_sha=sha,
                    details={"files": sorted(files)},
                )
            )
            session.commit()

            if settings.git_push_enabled:
                git_service.push()
                session.add(
                    VaultEvent(
                        event_type="autosave_push",
                        commit_sha=sha,
                    )
                )
                session.commit()

                publish_service.trigger_publish(
                    session,
                    trigger="autosave",
                    commit_sha=sha,
                )

            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc)
            session.commit()
            log.info("autosave complete: %s (%d files)", sha[:10], len(files))

        except Exception:
            job.status = "failed"
            job.completed_at = datetime.now(timezone.utc)
            import traceback

            job.error = traceback.format_exc()[-2000:]
            session.commit()
            log.exception("autosave failed")
        finally:
            session.close()


async def main() -> None:
    setup_logging()
    watcher = AutosaveWatcher()
    await watcher.run()


if __name__ == "__main__":
    asyncio.run(main())
