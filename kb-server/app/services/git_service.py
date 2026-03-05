"""Git CLI wrapper scoped to the vault repository."""

from __future__ import annotations

import logging
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings

log = logging.getLogger(__name__)


class GitError(Exception):
    pass


class RevupError(Exception):
    pass


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

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


def _run_revup(
    *args: str,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    cwd = cwd or settings.vault_path
    cmd = ["revup", *args]
    log.debug("revup %s (cwd=%s)", " ".join(args), cwd)
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        raise RevupError(
            f"revup {' '.join(args)} failed (rc={result.returncode}): "
            f"{result.stderr.strip()}"
        )
    return result


# ---------------------------------------------------------------------------
# Core git operations
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Revup topic helpers
# ---------------------------------------------------------------------------

_TOPIC_SAFE = re.compile(r"[^a-zA-Z0-9_-]")


def make_topic_name(files: list[str]) -> str:
    """Generate a deterministic, human-readable Revup topic name."""
    prefix = settings.revup_topic_prefix
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    if len(files) == 1:
        slug = _TOPIC_SAFE.sub("-", Path(files[0]).stem)[:40]
        return f"{prefix}/{ts}-{slug}"
    return f"{prefix}/{ts}-batch-{len(files)}"


def build_revup_commit_message(
    summary: str,
    topic: str,
    *,
    relative: str | None = None,
) -> str:
    """Build a commit message with Revup metadata trailers."""
    lines = [summary, "", f"Topic: {topic}"]
    if relative:
        lines.append(f"Relative: {relative}")
    return "\n".join(lines)


def commit_for_revup(files: list[str]) -> tuple[str, str] | None:
    """Stage, build a Revup-tagged commit, and return ``(sha, topic)``.

    Returns ``None`` when there is nothing to commit.
    """
    if not has_changes():
        log.info("revup commit: nothing to commit")
        return None

    stage_all()

    status = _run("status", "--porcelain", check=False)
    if not status.stdout.strip():
        log.info("revup commit: staging produced no committable changes")
        return None

    topic = make_topic_name(files)
    summary = f"kb-api: update {', '.join(files[:5])}"
    if len(files) > 5:
        summary += f" (+{len(files) - 5} more)"
    message = build_revup_commit_message(summary, topic)

    _run("commit", "-m", message)
    sha = _run("rev-parse", "HEAD").stdout.strip()
    log.info("revup committed %s topic=%s", sha[:10], topic)
    return sha, topic


def revup_upload(
    *,
    base_branch: str | None = None,
    skip_confirm: bool = True,
) -> str:
    """Run ``revup upload`` and return the combined stdout+stderr output."""
    base = base_branch or settings.revup_base_branch
    args = ["upload", "--base-branch", base]
    if skip_confirm:
        args.append("--skip-confirm")

    result = _run_revup(*args)
    output = (result.stdout + "\n" + result.stderr).strip()
    log.info("revup upload completed:\n%s", output)
    return output
