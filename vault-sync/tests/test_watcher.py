"""Tests for EchoGuard and SyncWatcher."""

import time
from pathlib import Path

import pytest

from vault_sync.watcher import EchoGuard, SyncWatcher


class TestEchoGuard:
    def test_marked_path_is_echo(self):
        g = EchoGuard(ttl=5.0)
        g.mark({"notes/a.md"})
        assert g.is_echo("notes/a.md") is True

    def test_unmarked_path_is_not_echo(self):
        g = EchoGuard(ttl=5.0)
        assert g.is_echo("notes/b.md") is False

    def test_echo_stays_active_within_ttl(self):
        g = EchoGuard(ttl=5.0)
        g.mark({"notes/a.md"})
        assert g.is_echo("notes/a.md") is True
        assert g.is_echo("notes/a.md") is True

    def test_expired_mark_is_not_echo(self):
        g = EchoGuard(ttl=0.01)
        g.mark({"notes/a.md"})
        time.sleep(0.02)
        assert g.is_echo("notes/a.md") is False


class TestSyncWatcher:
    def test_detects_new_file(self, tmp_path: Path):
        sync_dir = tmp_path / "sync"
        sync_dir.mkdir()

        guard = EchoGuard()
        watcher = SyncWatcher(sync_dir, guard)
        watcher.start()

        try:
            (sync_dir / "test.md").write_text("new file\n")
            time.sleep(0.5)
            changed, deleted = watcher.drain()
            assert "test.md" in changed
        finally:
            watcher.stop()

    def test_ignores_non_md_files(self, tmp_path: Path):
        sync_dir = tmp_path / "sync"
        sync_dir.mkdir()

        guard = EchoGuard()
        watcher = SyncWatcher(sync_dir, guard)
        watcher.start()

        try:
            (sync_dir / "script.py").write_text("code\n")
            time.sleep(0.5)
            changed, deleted = watcher.drain()
            assert "script.py" not in changed
        finally:
            watcher.stop()

    def test_suppresses_echo(self, tmp_path: Path):
        sync_dir = tmp_path / "sync"
        sync_dir.mkdir()

        guard = EchoGuard(ttl=5.0)
        guard.mark({"echo.md"})

        watcher = SyncWatcher(sync_dir, guard)
        watcher.start()

        try:
            (sync_dir / "echo.md").write_text("pulled content\n")
            time.sleep(0.5)
            changed, deleted = watcher.drain()
            assert "echo.md" not in changed
        finally:
            watcher.stop()

    def test_detects_deletion(self, tmp_path: Path):
        sync_dir = tmp_path / "sync"
        sync_dir.mkdir()
        (sync_dir / "bye.md").write_text("gone\n")

        guard = EchoGuard()
        watcher = SyncWatcher(sync_dir, guard)
        watcher.start()

        try:
            time.sleep(0.2)
            watcher.drain()
            (sync_dir / "bye.md").unlink()
            time.sleep(0.5)
            changed, deleted = watcher.drain()
            assert "bye.md" in deleted
        finally:
            watcher.stop()

    def test_drain_clears_accumulated(self, tmp_path: Path):
        sync_dir = tmp_path / "sync"
        sync_dir.mkdir()

        guard = EchoGuard()
        watcher = SyncWatcher(sync_dir, guard)
        watcher.start()

        try:
            (sync_dir / "a.md").write_text("a\n")
            time.sleep(0.5)
            changed1, _ = watcher.drain()
            assert "a.md" in changed1

            changed2, _ = watcher.drain()
            assert "a.md" not in changed2
        finally:
            watcher.stop()
