"""Core sync logic: pull the current view and push local edits."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from vault_sync.api_client import KBClient

log = logging.getLogger(__name__)

ALLOWED_EXTENSIONS: frozenset[str] = frozenset({".md", ".markdown", ".txt"})


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def pull_current(
    sync_dir: Path,
    client: KBClient,
    pending_local: set[str] | None = None,
) -> set[str]:
    """Refresh *sync_dir* from the server's ``current`` view.

    Returns the set of relative paths that were written or deleted locally.
    The caller can use this to suppress watcher echo.

    Args:
        sync_dir: Local directory to sync.
        client: API client for the kb-server.
        pending_local: Paths with pending local changes that should not be
            overwritten or deleted. This prevents pull from clobbering files
            the user is actively editing before they are pushed.
    """
    sync_dir.mkdir(parents=True, exist_ok=True)
    pending_local = pending_local or set()

    remote_notes = client.list_notes(view="current")
    remote_paths: set[str] = set()
    touched: set[str] = set()

    for item in remote_notes:
        rel_path = item["path"]
        remote_paths.add(rel_path)
        local_file = sync_dir / rel_path

        if rel_path in pending_local:
            log.debug("skipping %s (pending local changes)", rel_path)
            continue

        note = client.read_note(rel_path, view="current")
        content = note["content"]

        if local_file.is_file():
            existing = local_file.read_text(encoding="utf-8")
            if _content_hash(existing) == _content_hash(content):
                continue

        local_file.parent.mkdir(parents=True, exist_ok=True)
        local_file.write_text(content, encoding="utf-8")
        touched.add(rel_path)
        log.debug("pulled %s", rel_path)

    for local_file in sorted(sync_dir.rglob("*")):
        if not local_file.is_file():
            continue
        if local_file.suffix.lower() not in ALLOWED_EXTENSIONS:
            continue
        rel = str(local_file.relative_to(sync_dir))
        if rel not in remote_paths:
            if rel in pending_local:
                log.debug("skipping local-only %s (pending push)", rel)
                continue
            local_file.unlink()
            touched.add(rel)
            log.debug("removed local-only %s", rel)

    log.info("pull complete: %d files synced, %d touched", len(remote_paths), len(touched))
    return touched


def push_changes(
    sync_dir: Path,
    changed_files: set[str],
    deleted_files: set[str],
    client: KBClient,
) -> None:
    """Upload local modifications and deletions to the server."""
    for rel_path in sorted(changed_files):
        local_file = sync_dir / rel_path
        if not local_file.is_file():
            continue
        content = local_file.read_text(encoding="utf-8")
        try:
            client.write_note(rel_path, content)
            log.info("pushed %s", rel_path)
        except Exception:
            log.exception("failed to push %s", rel_path)

    for rel_path in sorted(deleted_files):
        try:
            client.delete_note(rel_path)
            log.info("pushed delete %s", rel_path)
        except Exception:
            log.exception("failed to push delete %s", rel_path)
