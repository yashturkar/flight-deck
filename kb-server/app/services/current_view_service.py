"""Service that builds a read-only *current* view.

The current view is defined as ``main`` content overlaid with pending
changes from open ``kb-api/*`` PR branches.  Nothing is checked out or
merged on disk -- all reads go through ``git show``.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.core.config import settings
from app.services import git_service, github_service
from app.services.vault_service import (
    ALLOWED_EXTENSIONS,
    NoteNotFound,
    PathNotAllowed,
    safe_resolve,
)

log = logging.getLogger(__name__)


def _pending_branches() -> list[str]:
    """Return branch names with open PRs matching the configured prefix.

    Tries the GitHub API first.  If that fails (token missing, network
    error, etc.) falls back to listing local branches that match the
    pattern.
    """
    prefix = settings.git_batch_branch_prefix
    try:
        prs = github_service.list_open_kb_api_prs()
        branches = [pr["head"]["ref"] for pr in prs if pr.get("head", {}).get("ref")]
        if branches:
            return branches
    except Exception:
        log.debug("GitHub PR lookup failed, falling back to local branches", exc_info=True)

    return git_service.list_branches(pattern=f"{prefix}/*")


def read_note_current(relative_path: str) -> tuple[str, datetime, list[str]]:
    """Read a note from the *current* view.

    Returns ``(content, modified_at, sources)`` where *sources* is the
    list of branches that contributed to the returned content.  The last
    branch in the list is the one whose content was used (last-write-wins).

    Raises ``NoteNotFound`` if the file is absent from both ``main`` and
    all pending branches.  Raises ``PathNotAllowed`` for invalid paths.
    """
    safe_resolve(relative_path)

    main_branch = settings.git_branch
    main_content = git_service.show_file(main_branch, relative_path)

    pending = _pending_branches()
    winning_content: str | None = main_content
    sources: list[str] = []
    if main_content is not None:
        sources.append(main_branch)

    for branch in pending:
        branch_content = git_service.show_file(branch, relative_path)
        if branch_content is not None:
            sources.append(branch)
            winning_content = branch_content

    if winning_content is None:
        raise NoteNotFound(f"No file at {relative_path}")

    now = datetime.now(timezone.utc)
    return winning_content, now, sources


def list_notes_current(prefix: str = "") -> list[tuple[str, datetime, list[str]]]:
    """List notes visible in the *current* view.

    Returns ``[(relative_path, modified_at, sources), ...]`` sorted by
    path.  Each entry includes which branches provide that file.
    """
    main_branch = settings.git_branch
    pending = _pending_branches()

    path_sources: dict[str, list[str]] = {}

    for path in git_service.list_tree(main_branch, prefix):
        if not any(path.endswith(ext) for ext in ALLOWED_EXTENSIONS):
            continue
        path_sources.setdefault(path, []).append(main_branch)

    for branch in pending:
        for path in git_service.list_tree(branch, prefix):
            if not any(path.endswith(ext) for ext in ALLOWED_EXTENSIONS):
                continue
            path_sources.setdefault(path, []).append(branch)

    now = datetime.now(timezone.utc)
    results = [
        (path, now, sources)
        for path, sources in sorted(path_sources.items())
    ]
    return results
