"""Git CLI wrapper scoped to the vault repository."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from app.core.config import settings

log = logging.getLogger(__name__)


class GitError(Exception):
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


def current_branch() -> str:
    """Return the name of the current branch."""
    return _run("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()


def branch_exists(branch: str) -> bool:
    """Check if a branch exists locally."""
    result = _run("rev-parse", "--verify", branch, check=False)
    return result.returncode == 0


def remote_branch_exists(branch: str, remote: str | None = None) -> bool:
    """Check if a branch exists on the remote."""
    remote = remote or settings.git_remote
    _run("fetch", remote, "--prune", check=False)
    result = _run("rev-parse", "--verify", f"{remote}/{branch}", check=False)
    return result.returncode == 0


def checkout(branch: str, create: bool = False) -> None:
    """Checkout a branch, optionally creating it."""
    if create:
        _run("checkout", "-b", branch)
    else:
        _run("checkout", branch)
    log.info("checked out branch %s", branch)


def checkout_or_create_from_main(branch: str) -> None:
    """Checkout branch if it exists, otherwise create from main."""
    main_branch = settings.git_branch
    remote = settings.git_remote

    if branch_exists(branch):
        checkout(branch)
        return

    if remote_branch_exists(branch, remote):
        _run("checkout", "-b", branch, f"{remote}/{branch}")
        log.info("checked out remote branch %s", branch)
        return

    checkout(main_branch)
    _run("pull", remote, main_branch, check=False)
    checkout(branch, create=True)
    log.info("created branch %s from %s", branch, main_branch)


def push_branch(branch: str, remote: str | None = None, retries: int = 2) -> None:
    """Push a specific branch to remote with retry."""
    remote = remote or settings.git_remote

    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            _run("push", "-u", remote, branch)
            log.info("pushed branch %s to %s", branch, remote)
            return
        except GitError as exc:
            last_err = exc
            log.warning("push branch attempt %d failed: %s", attempt, exc)

    raise GitError(f"push branch failed after {retries} attempts") from last_err


def return_to_main() -> None:
    """Return to the main branch."""
    main_branch = settings.git_branch
    checkout(main_branch)


# ---------------------------------------------------------------------------
# Batch commit helper
# ---------------------------------------------------------------------------

def commit_for_batch(files: list[str]) -> str | None:
    """Stage and create a batch commit for changed files (including deletions)."""
    stage_all()

    status = _run("status", "--porcelain", check=False)
    if not status.stdout.strip():
        log.info("batch commit: nothing to commit")
        return None

    summary = f"kb-api: update {', '.join(files[:5])}"
    if len(files) > 5:
        summary += f" (+{len(files) - 5} more)"
    _run("commit", "-m", summary)
    sha = _run("rev-parse", "HEAD").stdout.strip()
    log.info("batch committed %s", sha[:10])
    return sha
