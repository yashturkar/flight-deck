"""File-system watcher with echo suppression.

The watcher collects changed/deleted paths.  The main loop polls
``drain()`` at the configured debounce interval to pick them up.
"""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

log = logging.getLogger(__name__)

ALLOWED_EXTENSIONS: frozenset[str] = frozenset({".md", ".markdown", ".txt"})


class EchoGuard:
    """Suppress watcher events caused by pull writes.

    Call ``mark(paths)`` before writing pulled content.  The watcher
    checks ``is_echo(path)`` and skips marked paths.  Marks expire
    after *ttl* seconds so stale marks don't block real edits.
    """

    def __init__(self, ttl: float = 5.0) -> None:
        self._marks: dict[str, float] = {}
        self._lock = threading.Lock()
        self._ttl = ttl

    def mark(self, paths: set[str]) -> None:
        now = time.monotonic()
        with self._lock:
            for p in paths:
                self._marks[p] = now

    def is_echo(self, path: str) -> bool:
        with self._lock:
            ts = self._marks.get(path)
        if ts is None:
            return False
        if (time.monotonic() - ts) < self._ttl:
            return True
        with self._lock:
            self._marks.pop(path, None)
        return False


class _Handler(FileSystemEventHandler):
    """Collect changed/deleted paths, filtering out echo writes."""

    def __init__(self, sync_dir: Path, echo_guard: EchoGuard) -> None:
        self._sync_dir = sync_dir.resolve()
        self._echo_guard = echo_guard
        self._changed: set[str] = set()
        self._deleted: set[str] = set()
        self._lock = threading.Lock()

    def _rel(self, path: str) -> str | None:
        p = Path(path).resolve()
        if not p.is_relative_to(self._sync_dir):
            return None
        if p.suffix.lower() not in ALLOWED_EXTENSIONS:
            return None
        return str(p.relative_to(self._sync_dir))

    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        rel = self._rel(event.src_path)
        if rel and not self._echo_guard.is_echo(rel):
            with self._lock:
                self._changed.add(rel)

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        rel = self._rel(event.src_path)
        if rel and not self._echo_guard.is_echo(rel):
            with self._lock:
                self._changed.add(rel)

    def on_deleted(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        rel = self._rel(event.src_path)
        if rel and not self._echo_guard.is_echo(rel):
            with self._lock:
                self._deleted.add(rel)
                self._changed.discard(rel)

    def on_moved(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        old_rel = self._rel(event.src_path)
        new_rel = self._rel(event.dest_path)
        if old_rel and not self._echo_guard.is_echo(old_rel):
            with self._lock:
                self._deleted.add(old_rel)
                self._changed.discard(old_rel)
        if new_rel and not self._echo_guard.is_echo(new_rel):
            with self._lock:
                self._changed.add(new_rel)

    def drain(self) -> tuple[set[str], set[str]]:
        """Return and clear accumulated (changed, deleted) sets."""
        with self._lock:
            changed = set(self._changed)
            deleted = set(self._deleted)
            self._changed.clear()
            self._deleted.clear()
        return changed, deleted


class SyncWatcher:
    """Watch *sync_dir* and accumulate file-system events.

    Call ``drain()`` periodically from the main loop to collect changes.
    """

    def __init__(self, sync_dir: Path, echo_guard: EchoGuard) -> None:
        self._sync_dir = sync_dir.resolve()
        self._echo_guard = echo_guard
        self._handler = _Handler(self._sync_dir, echo_guard)
        self._observer = Observer()

    def start(self) -> None:
        self._sync_dir.mkdir(parents=True, exist_ok=True)
        self._observer.schedule(self._handler, str(self._sync_dir), recursive=True)
        self._observer.start()
        log.info("watching %s", self._sync_dir)

    def stop(self) -> None:
        self._observer.stop()
        self._observer.join()

    def drain(self) -> tuple[set[str], set[str]]:
        """Return ``(changed, deleted)`` and reset."""
        return self._handler.drain()
