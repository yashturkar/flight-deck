"""Unit tests for the autosave watcher debounce and flush logic."""

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.workers.autosave import AutosaveWatcher


@pytest.fixture()
def watcher(tmp_vault: Path):
    return AutosaveWatcher(vault_path=tmp_vault, debounce_seconds=1)


class TestDebounceLogic:
    def test_pending_starts_empty(self, watcher: AutosaveWatcher):
        assert len(watcher._pending) == 0

    @pytest.mark.asyncio
    async def test_flush_fires_after_debounce(self, watcher: AutosaveWatcher, tmp_vault: Path):
        """Simulate adding pending files and verify flush fires."""
        watcher._pending.add("notes/test.md")

        flush_called = asyncio.Event()
        original_do_autosave = watcher._do_autosave

        def mock_autosave(files):
            flush_called.set()

        with patch.object(watcher, "_do_autosave", side_effect=mock_autosave):
            watcher._reset_timer()
            await asyncio.wait_for(flush_called.wait(), timeout=3)

        assert len(watcher._pending) == 0

    @pytest.mark.asyncio
    async def test_timer_reset_extends_debounce(self, watcher: AutosaveWatcher):
        """Resetting the timer should cancel the previous flush."""
        flush_called = asyncio.Event()

        def mock_autosave(files):
            flush_called.set()

        with patch.object(watcher, "_do_autosave", side_effect=mock_autosave):
            watcher._pending.add("notes/a.md")
            watcher._reset_timer()

            await asyncio.sleep(0.5)

            watcher._pending.add("notes/b.md")
            watcher._reset_timer()

            await asyncio.sleep(0.5)

            assert watcher._flush_task is not None
            assert not watcher._flush_task.done()

            await asyncio.wait_for(flush_called.wait(), timeout=3)


class TestFilter:
    def test_ignores_git_directory(self, watcher: AutosaveWatcher):
        from watchfiles import Change

        assert watcher._filter(Change.modified, "/vault/.git/objects/abc") is False

    def test_accepts_markdown(self, watcher: AutosaveWatcher):
        from watchfiles import Change

        assert watcher._filter(Change.modified, "/vault/notes/hello.md") is True

    def test_rejects_non_content(self, watcher: AutosaveWatcher):
        from watchfiles import Change

        assert watcher._filter(Change.modified, "/vault/image.png") is False


class TestActorRouting:
    def test_autosave_commits_and_pushes_as_user(self, watcher: AutosaveWatcher):
        with patch("app.workers.autosave.git_service") as gs, \
             patch("app.workers.autosave.SessionLocal") as sl, \
             patch("app.workers.autosave.publish_service.trigger_publish"):
            mock_session = MagicMock()
            sl.return_value = mock_session
            gs.commit_files.return_value = "a" * 40

            watcher._do_autosave({"notes/test.md"})

            gs.commit_files.assert_called_once()
            assert gs.commit_files.call_args.kwargs["actor"] == gs.USER_ACTOR
            gs.push.assert_called_once_with(actor=gs.USER_ACTOR)
