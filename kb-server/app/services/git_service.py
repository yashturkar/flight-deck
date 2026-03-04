"""Git CLI wrapper scoped to the vault repository."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from app.core.config import settings

log = logging.getLogger(__name__)


class GitError(Exception):
    pass


def _run(
    *args: str,
    cwd: Path | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    cwd = cwd or settings.vault_path
    cmd = ["git", *args]
    log.debug("git %s (cwd=%s)", " ".join(args), cwd)
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if check and result.returncode != 0:
        raise GitError(
            f"git {' '.join(args)} failed (rc={result.returncode}): "
            f"{result.stderr.strip()}"
        )
    return result


def has_changes() -> bool:
    """True if the working tree has staged or unstaged changes."""
    result = _run("status", "--porcelain", check=False)
    return bool(result.stdout.strip())


def stage_all() -> None:
    _run("add", "--all")


def commit(message: str) -> str | None:
    """Create a commit and return the SHA, or ``None`` if nothing to commit."""
    if not has_changes():
        log.info("nothing to commit")
        return None

    stage_all()

    # Re-check after staging (e.g. only whitespace / gitignored files)
    status = _run("status", "--porcelain", check=False)
    if not status.stdout.strip():
        log.info("staging produced no committable changes")
        return None

    _run("commit", "-m", message)
    sha = _run("rev-parse", "HEAD").stdout.strip()
    log.info("committed %s: %s", sha[:10], message)
    return sha


def push(
    remote: str | None = None,
    branch: str | None = None,
    retries: int = 2,
) -> None:
    """Push to remote with simple retry on transient failures."""
    remote = remote or settings.git_remote
    branch = branch or settings.git_branch

    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            _run("push", remote, branch)
            log.info("pushed %s/%s", remote, branch)
            return
        except GitError as exc:
            last_err = exc
            log.warning("push attempt %d failed: %s", attempt, exc)

    raise GitError(f"push failed after {retries} attempts") from last_err


def current_sha() -> str:
    return _run("rev-parse", "HEAD").stdout.strip()
