"""Filesystem operations scoped to the canonical vault."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from app.core.config import settings

log = logging.getLogger(__name__)

ALLOWED_EXTENSIONS: set[str] = {".md", ".markdown", ".txt"}


class PathNotAllowed(Exception):
    pass


class NoteNotFound(Exception):
    pass


def _vault_root() -> Path:
    return settings.vault_path.resolve()


def safe_resolve(relative_path: str) -> Path:
    """Return an absolute path guaranteed to be inside the vault.

    Rejects absolute input, ``..`` traversal, symlink escapes, and
    extensions outside the allow-list.
    """
    cleaned = PurePosixPath(relative_path)

    if cleaned.is_absolute():
        raise PathNotAllowed("Absolute paths are not accepted")

    for part in cleaned.parts:
        if part in {".", ".."}:
            raise PathNotAllowed("Relative traversal segments are not allowed")

    resolved = (_vault_root() / cleaned).resolve()

    if not resolved.is_relative_to(_vault_root()):
        raise PathNotAllowed("Resolved path escapes the vault root")

    if resolved.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise PathNotAllowed(
            f"Extension '{resolved.suffix}' is not in the allow-list"
        )

    return resolved


def read_note(relative_path: str) -> tuple[str, datetime]:
    """Return ``(content, modified_at)`` for a note inside the vault."""
    target = safe_resolve(relative_path)

    if not target.is_file():
        raise NoteNotFound(f"No file at {relative_path}")

    content = target.read_text(encoding="utf-8")
    mtime = datetime.fromtimestamp(target.stat().st_mtime, tz=timezone.utc)
    return content, mtime


def write_note(relative_path: str, content: str) -> datetime:
    """Write *content* to a note, creating parent directories if needed.

    Returns the new modification timestamp.
    """
    target = safe_resolve(relative_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    mtime = datetime.fromtimestamp(target.stat().st_mtime, tz=timezone.utc)
    log.info("wrote %s (%d bytes)", relative_path, len(content))
    return mtime


def delete_note(relative_path: str) -> None:
    """Delete a note from the vault.

    Raises ``NoteNotFound`` if the file does not exist.
    """
    target = safe_resolve(relative_path)

    if not target.is_file():
        raise NoteNotFound(f"No file at {relative_path}")

    target.unlink()
    log.info("deleted %s", relative_path)


def list_notes(prefix: str = "") -> list[tuple[str, datetime]]:
    """List all notes under *prefix* (relative to vault root).

    Returns ``[(relative_path, modified_at), ...]`` sorted by path.
    """
    root = _vault_root()
    search_root = root / prefix if prefix else root

    if not search_root.is_dir():
        return []

    results: list[tuple[str, datetime]] = []
    for p in sorted(search_root.rglob("*")):
        if not p.is_file():
            continue
        if p.suffix.lower() not in ALLOWED_EXTENSIONS:
            continue
        rel = str(p.relative_to(root))
        mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
        results.append((rel, mtime))
    return results
