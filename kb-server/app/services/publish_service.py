"""Quartz publish trigger — command or webhook, with DB tracking."""

from __future__ import annotations

import logging
import subprocess
from datetime import datetime, timezone

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.db import PublishRun

log = logging.getLogger(__name__)


def _is_enabled() -> bool:
    return bool(settings.quartz_build_command or settings.quartz_webhook_url)


def trigger_publish(
    session: Session,
    trigger: str = "manual",
    commit_sha: str | None = None,
) -> PublishRun | None:
    """Run Quartz build and persist the result.

    Returns the ``PublishRun`` row, or ``None`` if publishing is not
    configured.
    """
    if not _is_enabled():
        log.info("publish skipped — no build command or webhook configured")
        return None

    run = PublishRun(
        trigger=trigger,
        status="running",
        commit_sha=commit_sha,
    )
    session.add(run)
    session.commit()

    try:
        if settings.quartz_build_command:
            _run_command(settings.quartz_build_command)
        elif settings.quartz_webhook_url:
            _post_webhook(settings.quartz_webhook_url)

        run.status = "completed"
        log.info("publish %d completed (trigger=%s)", run.id, trigger)

    except Exception as exc:
        run.status = "failed"
        run.error = str(exc)[:2000]
        log.error("publish %d failed: %s", run.id, exc)

    finally:
        run.completed_at = datetime.now(timezone.utc)
        session.commit()

    return run


def _run_command(cmd: str) -> None:
    log.info("running quartz build command: %s", cmd)
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"quartz build failed (rc={result.returncode}): "
            f"{result.stderr.strip()[:500]}"
        )


def _post_webhook(url: str) -> None:
    log.info("posting quartz webhook: %s", url)
    resp = httpx.post(url, timeout=30)
    resp.raise_for_status()
