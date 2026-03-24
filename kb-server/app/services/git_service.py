"""Git CLI wrapper scoped to the vault repository."""

from __future__ import annotations

import logging
import os
import stat
import subprocess
import tempfile
from enum import Enum
from pathlib import Path

from app.core.config import settings

log = logging.getLogger(__name__)


class GitActor(str, Enum):
    """Actor identity for git operations.

    Use ``USER`` for human-origin writes on the configured base branch and
    ``AGENT`` for API/batch workflows that operate on kb-api/* branches.
    """

    USER = "user"
    AGENT = "agent"


USER_ACTOR = GitActor.USER
AGENT_ACTOR = GitActor.AGENT


class GitError(Exception):
    pass


def _auth_failure_hint(stderr: str, stdout: str) -> str | None:
    """Return a remediation hint when git output indicates auth failure."""
    text = f"{stderr}\n{stdout}".lower()
    auth_markers = (
        "authentication failed",
        "invalid username or token",
        "password authentication is not supported",
        "could not read username",
        "could not read password",
        "terminal prompts disabled",
    )
    if any(marker in text for marker in auth_markers):
        return (
            "Git authentication failed. Configure non-interactive credentials "
            "for the remote (SSH key or PAT-backed credential helper). "
            "Interactive username/password prompts are disabled."
        )
    return None


def _ensure_askpass_script(token: str) -> str:
    """Create a tiny GIT_ASKPASS script that echoes the given token.

    Returns the path to the script.  The file is written once per token
    value and reused across calls.
    """
    script_dir = Path(tempfile.gettempdir()) / "kb-server-askpass"
    script_dir.mkdir(exist_ok=True)
    # One script per token hash so we don't leak tokens in filenames
    import hashlib

    token_hash = hashlib.sha256(token.encode()).hexdigest()[:12]
    script_path = script_dir / f"askpass-{token_hash}"
    if not script_path.exists():
        script_path.write_text(f"#!/bin/sh\necho '{token}'\n")
        script_path.chmod(stat.S_IRWXU)
    return str(script_path)


def _actor_env(actor: GitActor | None) -> dict[str, str]:
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GCM_INTERACTIVE"] = "never"
    if actor is None:
        return env

    if actor == USER_ACTOR:
        author_name = settings.git_user_author_name
        author_email = settings.git_user_author_email
        committer_name = settings.git_user_committer_name or author_name
        committer_email = settings.git_user_committer_email or author_email
        ssh_command = settings.git_user_ssh_command
        https_token = ""
    elif actor == AGENT_ACTOR:
        author_name = settings.git_agent_author_name
        author_email = settings.git_agent_author_email
        committer_name = settings.git_agent_committer_name or author_name
        committer_email = settings.git_agent_committer_email or author_email
        ssh_command = settings.git_agent_ssh_command
        https_token = settings.git_agent_https_token
    else:
        raise GitError(f"unsupported git actor: {actor}")

    if author_name:
        env["GIT_AUTHOR_NAME"] = author_name
    if author_email:
        env["GIT_AUTHOR_EMAIL"] = author_email
    if committer_name:
        env["GIT_COMMITTER_NAME"] = committer_name
    if committer_email:
        env["GIT_COMMITTER_EMAIL"] = committer_email
    if ssh_command:
        env["GIT_SSH_COMMAND"] = ssh_command
    if https_token:
        # Rewrite the remote URL to embed the token so git never consults
        # credential helpers.  This works regardless of how many helpers
        # are configured (osxkeychain, store, etc.).
        env["GIT_CONFIG_COUNT"] = "1"
        env["GIT_CONFIG_KEY_0"] = "url.https://x-access-token:" + https_token + "@github.com/.insteadOf"
        env["GIT_CONFIG_VALUE_0"] = "https://github.com/"

    return env


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def _run(
    *args: str,
    cwd: Path | None = None,
    check: bool = True,
    actor: GitActor | None = None,
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
        env=_actor_env(actor),
    )
    if check and result.returncode != 0:
        hint = _auth_failure_hint(result.stderr, result.stdout)
        if hint:
            raise GitError(
                f"git {' '.join(args)} failed (rc={result.returncode}): "
                f"{result.stderr.strip()} | {hint}"
            )
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


def stage_all(actor: GitActor | None = None) -> None:
    _run("add", "--all", actor=actor)


def stage_files(files: list[str], actor: GitActor | None = None) -> None:
    """Stage specific files (supports additions, modifications, and deletions)."""
    if not files:
        return
    _run("add", "--", *files, actor=actor)


def commit(message: str, actor: GitActor | None = None) -> str | None:
    """Create a commit and return the SHA, or ``None`` if nothing to commit."""
    if not has_changes():
        log.info("nothing to commit")
        return None

    stage_all(actor=actor)

    status = _run("status", "--porcelain", check=False, actor=actor)
    if not status.stdout.strip():
        log.info("staging produced no committable changes")
        return None

    _run("commit", "-m", message, actor=actor)
    sha = _run("rev-parse", "HEAD", actor=actor).stdout.strip()
    log.info("committed %s: %s", sha[:10], message)
    return sha


def commit_files(
    files: list[str], message: str, actor: GitActor | None = None
) -> str | None:
    """Stage and commit only the specified files.
    
    Returns the SHA, or None if nothing to commit.
    """
    if not files:
        log.info("no files to commit")
        return None
    
    stage_files(files, actor=actor)
    
    status = _run("status", "--porcelain", check=False, actor=actor)
    if not status.stdout.strip():
        log.info("staging produced no committable changes")
        return None
    
    _run("commit", "-m", message, actor=actor)
    sha = _run("rev-parse", "HEAD", actor=actor).stdout.strip()
    log.info("committed %s: %s", sha[:10], message)
    return sha


def push(retries: int = 2) -> None:
    """Push the configured remote/base branch for human-origin writes.

    This helper is intentionally user-only; agent writes use ``push_branch()``
    on kb-api/* branches.

    See also: ``push_branch()``.
    """
    remote = settings.git_remote
    branch = settings.git_branch

    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            _run("push", remote, branch, actor=USER_ACTOR)
            log.info("pushed %s/%s", remote, branch)
            return
        except GitError as exc:
            last_err = exc
            log.warning("push attempt %d failed: %s", attempt, exc)

    raise GitError(f"push failed after {retries} attempts") from last_err


def pull(
    remote: str | None = None,
    branch: str | None = None,
    actor: GitActor | None = None,
) -> bool:
    """Pull from remote. Returns True if new commits were fetched.
    
    Uses rebase strategy to handle diverged branches cleanly.
    Skips if there are uncommitted local changes.
    """
    remote = remote or settings.git_remote
    branch = branch or settings.git_branch

    if has_changes():
        log.debug("pull skipped: uncommitted local changes")
        return False

    old_sha = current_sha()

    _run("fetch", remote, branch, check=False, actor=actor)

    result = _run("pull", "--rebase", remote, branch, check=False, actor=actor)
    if result.returncode != 0:
        stderr = result.stderr.strip()
        if "Already up to date" in result.stdout or "Already up to date" in stderr:
            return False
        if "CONFLICT" in stderr or "could not apply" in stderr.lower():
            log.warning("pull rebase conflict, aborting rebase")
            _run("rebase", "--abort", check=False)
            return False
        log.warning("pull failed: %s", stderr)
        return False

    new_sha = current_sha()
    if new_sha != old_sha:
        log.info("pulled new commits: %s -> %s", old_sha[:10], new_sha[:10])
        return True

    return False


def current_sha() -> str:
    return _run("rev-parse", "HEAD").stdout.strip()


def show_file(branch: str, path: str) -> str | None:
    """Read file content from a branch without checking it out.

    Returns the file contents as a string, or ``None`` if the file does
    not exist on that branch.
    """
    result = _run("show", f"{branch}:{path}", check=False)
    if result.returncode != 0:
        return None
    return result.stdout


def list_branches(pattern: str | None = None) -> list[str]:
    """Return local branch names, optionally filtered by a glob *pattern*."""
    args = ["branch", "--list", "--format=%(refname:short)"]
    if pattern:
        args.append(pattern)
    result = _run(*args, check=False)
    if result.returncode != 0 or not result.stdout.strip():
        return []
    return [b.strip() for b in result.stdout.strip().splitlines() if b.strip()]


def list_tree(branch: str, prefix: str = "") -> list[str]:
    """List file paths on *branch* under *prefix* using ``git ls-tree``.

    Returns paths relative to the repository root (blobs only).
    """
    target = f"{branch}:{prefix}" if prefix else branch
    result = _run("ls-tree", "-r", "--name-only", target, check=False)
    if result.returncode != 0 or not result.stdout.strip():
        return []
    lines = [p.strip() for p in result.stdout.strip().splitlines() if p.strip()]
    if prefix:
        pfx = prefix.rstrip("/") + "/"
        lines = [pfx + p for p in lines]
    return lines


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


def stash_changes(actor: GitActor | None = None) -> bool:
    """Stash any uncommitted changes including untracked files.
    
    Returns True if something was stashed.
    """
    if not has_changes():
        return False
    _run(
        "stash",
        "push",
        "--include-untracked",
        "-m",
        "kb-server-auto-stash",
        actor=actor,
    )
    log.debug("stashed local changes (including untracked)")
    return True


def stash_pop(actor: GitActor | None = None) -> bool:
    """Pop the most recent stash if it exists.
    
    Returns True if stash was popped successfully, False if no stash or conflict.
    Handles the case where untracked files in the stash already exist on disk.
    """
    result = _run("stash", "list", check=False)
    if "kb-server-auto-stash" not in result.stdout:
        log.debug("no stash to pop")
        return False
    
    # Show what's in the stash before popping
    stash_show = _run(
        "stash",
        "show",
        "--stat",
        "--include-untracked",
        check=False,
        actor=actor,
    )
    log.debug("stash contents: %s", stash_show.stdout.strip())
    
    pop_result = _run("stash", "pop", check=False, actor=actor)
    if pop_result.returncode != 0:
        stderr = pop_result.stderr.strip()
        
        if "already exists" in stderr or "could not restore untracked files" in stderr:
            # Untracked files in stash conflict with existing files
            # Parse the error to find which files are blocking
            log.info("stash pop blocked by existing files, extracting manually")
            log.debug("stash pop stderr: %s", stderr)
            
            # Extract blocking file names from error message
            # Format: "path/to/file.md already exists, no checkout"
            blocking_files = []
            for line in stderr.split("\n"):
                if "already exists" in line:
                    # Extract the file path (everything before " already exists")
                    file_path = line.split(" already exists")[0].strip()
                    if file_path:
                        blocking_files.append(file_path)
            
            log.debug("blocking files parsed: %s", blocking_files)
            
            # Remove existing files that block the stash
            cwd = settings.vault_path
            for f in blocking_files:
                file_path = cwd / f
                log.debug("checking file %s exists: %s", file_path, file_path.exists())
                if file_path.exists():
                    file_path.unlink()
                    log.info("removed blocking file: %s", f)
            
            # Try pop again
            retry_result = _run("stash", "pop", check=False, actor=actor)
            log.debug("retry pop result: rc=%d stdout=%s stderr=%s", 
                     retry_result.returncode, retry_result.stdout.strip(), retry_result.stderr.strip())
            if retry_result.returncode != 0:
                # Last resort: apply stash without index, then drop
                log.warning("retry pop failed (%s), trying to extract from stash tree", retry_result.stderr.strip())
                # Use git show to extract the stashed file content directly
                # stash@{0}^3 is the untracked files tree in a stash
                tree_result = _run(
                    "ls-tree",
                    "-r",
                    "--name-only",
                    "stash@{0}^3",
                    check=False,
                    actor=actor,
                )
                log.debug("stash^3 tree: rc=%d files=%s", tree_result.returncode, tree_result.stdout.strip())
                if tree_result.returncode == 0 and tree_result.stdout.strip():
                    for f in tree_result.stdout.strip().split("\n"):
                        f = f.strip()
                        if not f:
                            continue
                        # Remove if exists, then checkout from stash
                        file_path = cwd / f
                        if file_path.exists():
                            file_path.unlink()
                        checkout_result = _run(
                            "checkout",
                            "stash@{0}^3",
                            "--",
                            f,
                            check=False,
                            actor=actor,
                        )
                        log.info("extracted from stash: %s (rc=%d)", f, checkout_result.returncode)
                else:
                    log.warning("no untracked files in stash^3, stash may have been dropped")
                _run("stash", "drop", check=False, actor=actor)
            
            # Verify we have changes now
            if has_changes():
                log.info("restored stashed changes successfully")
            else:
                # Check if the file exists but content is identical
                status = _run("status", "--porcelain", check=False, actor=actor)
                diff = _run("diff", "HEAD", check=False, actor=actor)
                log.warning(
                    "stash extraction completed but no changes detected! "
                    "status=%s diff_len=%d (content may be identical to committed version)",
                    status.stdout.strip() or "(clean)",
                    len(diff.stdout)
                )
            return True
            
        elif "CONFLICT" in stderr or "conflict" in stderr.lower():
            log.warning("stash pop conflict, attempting to resolve by keeping stashed version")
            # Accept "theirs" (the stashed version) for conflicts
            _run("checkout", "--theirs", ".", check=False, actor=actor)
            _run("add", "--all", check=False, actor=actor)
            # Drop the stash since we've manually applied it
            _run("stash", "drop", check=False, actor=actor)
            log.debug("resolved stash conflict")
            return True
        else:
            log.warning("stash pop failed: %s", stderr)
            return False
    
    # Check if we actually have changes after pop
    if has_changes():
        log.debug("restored stashed changes (has uncommitted changes)")
    else:
        log.debug("stash popped but no changes detected (content may be identical)")
    
    return True


def checkout(branch: str, create: bool = False, actor: GitActor | None = None) -> None:
    """Checkout a branch, optionally creating it."""
    if create:
        _run("checkout", "-b", branch, actor=actor)
    else:
        _run("checkout", branch, actor=actor)
    log.info("checked out branch %s", branch)


def checkout_or_create_from_main(
    branch: str, stash: bool = True, actor: GitActor | None = None
) -> bool:
    """Checkout branch if it exists, otherwise create from main.
    
    If stash=True, stashes uncommitted changes before checkout and returns True
    if changes were stashed (caller should call stash_pop after committing).
    
    When checking out an existing branch, rebases it on main to pick up any
    merged changes.
    """
    main_branch = settings.git_branch
    remote = settings.git_remote

    stashed = False
    if stash and has_changes():
        stashed = stash_changes(actor=actor)

    try:
        if branch_exists(branch):
            checkout(branch, actor=actor)
            # Rebase on main to pick up any merged changes (like deletions)
            _run("fetch", remote, main_branch, check=False, actor=actor)
            log.debug("rebasing %s onto %s/%s", branch, remote, main_branch)
            rebase_result = _run(
                "rebase", f"{remote}/{main_branch}", check=False, actor=actor
            )
            if rebase_result.returncode != 0:
                if "CONFLICT" in rebase_result.stderr:
                    log.warning("rebase conflict on %s, aborting rebase", branch)
                    _run("rebase", "--abort", check=False, actor=actor)
                else:
                    log.debug("rebase result: %s %s", rebase_result.stdout.strip(), rebase_result.stderr.strip())
            else:
                log.info("rebased %s onto %s/%s", branch, remote, main_branch)
            return stashed

        if remote_branch_exists(branch, remote):
            _run("checkout", "-b", branch, f"{remote}/{branch}", actor=actor)
            log.info("checked out remote branch %s", branch)
            # Also rebase on main
            _run("fetch", remote, main_branch, check=False, actor=actor)
            rebase_result = _run(
                "rebase", f"{remote}/{main_branch}", check=False, actor=actor
            )
            if rebase_result.returncode != 0 and "CONFLICT" in rebase_result.stderr:
                log.warning("rebase conflict on %s, aborting rebase", branch)
                _run("rebase", "--abort", check=False, actor=actor)
            return stashed

        checkout(main_branch, actor=actor)
        _run("pull", remote, main_branch, check=False, actor=actor)
        checkout(branch, create=True, actor=actor)
        log.info("created branch %s from %s", branch, main_branch)
        return stashed
    except GitError:
        if stashed:
            stash_pop(actor=actor)
        raise


def push_branch(
    branch: str,
    remote: str | None = None,
    retries: int = 2,
    actor: GitActor | None = None,
) -> None:
    """Push a specific branch to remote with retry.
    
    If push fails due to non-fast-forward (remote has diverged), attempts
    to pull --rebase before retrying.
    """
    remote = remote or settings.git_remote

    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            _run("push", "-u", remote, branch, actor=actor)
            log.info("pushed branch %s to %s", branch, remote)
            return
        except GitError as exc:
            last_err = exc
            log.warning("push branch attempt %d failed: %s", attempt, exc)
            
            if "non-fast-forward" in str(exc) or "rejected" in str(exc):
                log.info("attempting pull --rebase to resolve diverged branch")
                rebase_result = _run(
                    "pull", "--rebase", remote, branch, check=False, actor=actor
                )
                if rebase_result.returncode != 0:
                    stderr = rebase_result.stderr.strip()
                    if "CONFLICT" in stderr or "could not apply" in stderr.lower():
                        log.warning("rebase conflict, aborting")
                        _run("rebase", "--abort", check=False, actor=actor)
                    else:
                        log.warning("pull --rebase failed: %s", stderr)

    raise GitError(f"push branch failed after {retries} attempts") from last_err


def return_to_main() -> None:
    """Return to the main branch."""
    main_branch = settings.git_branch
    checkout(main_branch)


# ---------------------------------------------------------------------------
# Batch commit helper
# ---------------------------------------------------------------------------

def commit_for_batch(
    files: list[str], actor: GitActor | None = None
) -> str | None:
    """Stage and create a batch commit for changed files (including deletions)."""
    stage_all(actor=actor)

    status = _run("status", "--porcelain", check=False, actor=actor)
    status_output = status.stdout.strip()
    if not status_output:
        log.info("batch commit: nothing to commit")
        # Log what files we expected to commit for debugging
        log.debug("batch commit: expected files were: %s", files)
        return None

    log.debug("batch commit: staging status:\n%s", status_output)
    
    summary = f"kb-api: update {', '.join(files[:5])}"
    if len(files) > 5:
        summary += f" (+{len(files) - 5} more)"
    _run("commit", "-m", summary, actor=actor)
    sha = _run("rev-parse", "HEAD", actor=actor).stdout.strip()
    log.info("batch committed %s", sha[:10])
    return sha
