"""Debounced batcher that collects API note-writes, commits, and runs revup upload.

Usage
-----
Call ``enqueue(path)`` after each successful API write.  A background
thread waits for the configured debounce window, then commits all
queued paths with Revup metadata and triggers ``revup upload``.

The batcher is a singleton — import and use the module-level ``batcher``
instance.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone

from app.core.config import settings
from app.models.db import Job, SessionLocal, VaultEvent
from app.services import git_service

log = logging.getLogger(__name__)


class RevupBatcher:
    def __init__(self, debounce_seconds: int | None = None):
        self.debounce_seconds = (
            debounce_seconds
            if debounce_seconds is not None
            else settings.revup_batch_debounce_seconds
        )
        self._pending: set[str] = set()
        self._lock = threading.Lock()
        self._timer: threading.Timer | None = None

    def enqueue(self, path: str) -> None:
        """Add *path* to the current batch and reset the debounce timer.

        Thread-safe — safe to call from sync FastAPI route handlers.
        """
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

        self._do_commit_and_upload(files)

    def _do_commit_and_upload(self, files: list[str]) -> None:
        session = SessionLocal()
        try:
            job = Job(
                job_type="revup_batch",
                status="running",
                meta={"files": files},
            )
            session.add(job)
            session.commit()

            result = git_service.commit_for_revup(files)
            if result is None:
                job.status = "skipped"
                job.completed_at = datetime.now(timezone.utc)
                session.commit()
                log.info("revup batch skipped — nothing to commit")
                return

            sha, topic = result

            session.add(
                VaultEvent(
                    event_type="revup_commit",
                    commit_sha=sha,
                    details={"files": files, "topic": topic},
                )
            )
            session.commit()

            try:
                output = git_service.revup_upload()
            except git_service.RevupError as exc:
                log.error("revup upload failed: %s", exc)
                session.add(
                    VaultEvent(
                        event_type="revup_upload_failed",
                        commit_sha=sha,
                        details={"error": str(exc)[:2000], "topic": topic},
                    )
                )
                job.status = "failed"
                job.error = str(exc)[:2000]
                job.completed_at = datetime.now(timezone.utc)
                session.commit()
                return

            session.add(
                VaultEvent(
                    event_type="revup_upload",
                    commit_sha=sha,
                    details={
                        "topic": topic,
                        "output": output[:2000],
                    },
                )
            )
            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc)
            session.commit()
            log.info(
                "revup batch complete: topic=%s sha=%s (%d files)",
                topic,
                sha[:10],
                len(files),
            )

        except Exception:
            import traceback

            job.status = "failed"
            job.error = traceback.format_exc()[-2000:]
            job.completed_at = datetime.now(timezone.utc)
            session.commit()
            log.exception("revup batch failed")
        finally:
            session.close()


batcher = RevupBatcher()
