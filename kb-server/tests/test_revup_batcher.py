"""Unit tests for the Revup batching service."""

from __future__ import annotations

import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.revup_batcher import RevupBatcher


@pytest.fixture()
def batcher_fast():
    """Batcher with 1-second debounce for fast tests."""
    with patch("app.services.revup_batcher.settings") as s:
        s.revup_batch_debounce_seconds = 1
        return RevupBatcher(debounce_seconds=1)


class TestEnqueueAndDebounce:
    def test_single_write_flushes_after_debounce(self, batcher_fast: RevupBatcher):
        flush_called = threading.Event()
        captured_files: list[list[str]] = []

        def mock_commit_and_upload(files: list[str]) -> None:
            captured_files.append(files)
            flush_called.set()

        with patch.object(batcher_fast, "_do_commit_and_upload", side_effect=mock_commit_and_upload):
            batcher_fast.enqueue("notes/a.md")
            assert flush_called.wait(timeout=3)

        assert len(captured_files) == 1
        assert captured_files[0] == ["notes/a.md"]

    def test_multiple_writes_batched_into_one_flush(self, batcher_fast: RevupBatcher):
        flush_called = threading.Event()
        captured_files: list[list[str]] = []

        def mock_commit_and_upload(files: list[str]) -> None:
            captured_files.append(files)
            flush_called.set()

        with patch.object(batcher_fast, "_do_commit_and_upload", side_effect=mock_commit_and_upload):
            batcher_fast.enqueue("notes/a.md")
            time.sleep(0.2)
            batcher_fast.enqueue("notes/b.md")
            time.sleep(0.2)
            batcher_fast.enqueue("notes/c.md")

            assert flush_called.wait(timeout=3)

        assert len(captured_files) == 1
        assert captured_files[0] == ["notes/a.md", "notes/b.md", "notes/c.md"]

    def test_empty_pending_does_not_flush(self, batcher_fast: RevupBatcher):
        flush_called = threading.Event()

        def mock_commit_and_upload(files: list[str]) -> None:
            flush_called.set()

        with patch.object(batcher_fast, "_do_commit_and_upload", side_effect=mock_commit_and_upload):
            batcher_fast._reset_timer()
            assert not flush_called.wait(timeout=2)


class TestDoCommitAndUpload:
    def test_skips_when_nothing_to_commit(self, batcher_fast: RevupBatcher):
        with patch("app.services.revup_batcher.git_service") as gs, \
             patch("app.services.revup_batcher.SessionLocal") as sl:
            gs.commit_for_revup.return_value = None
            mock_session = MagicMock()
            sl.return_value = mock_session

            batcher_fast._do_commit_and_upload(["notes/a.md"])

            gs.revup_upload.assert_not_called()

    def test_calls_revup_upload_on_commit(self, batcher_fast: RevupBatcher):
        with patch("app.services.revup_batcher.git_service") as gs, \
             patch("app.services.revup_batcher.SessionLocal") as sl:
            gs.commit_for_revup.return_value = ("abc123" + "0" * 34, "kb-api/t1")
            gs.revup_upload.return_value = "PR created"
            mock_session = MagicMock()
            sl.return_value = mock_session

            batcher_fast._do_commit_and_upload(["notes/a.md"])

            gs.revup_upload.assert_called_once()

    def test_handles_revup_upload_failure(self, batcher_fast: RevupBatcher):
        from app.services.git_service import RevupError

        with patch("app.services.revup_batcher.git_service") as gs, \
             patch("app.services.revup_batcher.SessionLocal") as sl:
            gs.commit_for_revup.return_value = ("abc123" + "0" * 34, "kb-api/t1")
            gs.RevupError = RevupError
            gs.revup_upload.side_effect = RevupError("upload failed")
            mock_session = MagicMock()
            sl.return_value = mock_session

            batcher_fast._do_commit_and_upload(["notes/a.md"])

            add_calls = mock_session.add.call_args_list
            event_types = [
                c.args[0].event_type
                for c in add_calls
                if hasattr(c.args[0], "event_type")
            ]
            assert "revup_upload_failed" in event_types
