"""Unit tests for the Git batching service."""

from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from app.services.git_batcher import GitBatcher


@pytest.fixture()
def batcher_fast():
    """Batcher with 1-second debounce for fast tests."""
    with patch("app.services.git_batcher.settings") as s:
        s.git_batch_debounce_seconds = 1
        s.git_batch_branch_prefix = "kb-api"
        return GitBatcher(debounce_seconds=1)


class TestEnqueueAndDebounce:
    def test_single_write_flushes_after_debounce(self, batcher_fast: GitBatcher):
        flush_called = threading.Event()
        captured_files: list[list[str]] = []

        def mock_commit_and_pr(files: list[str]) -> None:
            captured_files.append(files)
            flush_called.set()

        with patch.object(batcher_fast, "_do_commit_and_pr", side_effect=mock_commit_and_pr):
            batcher_fast.enqueue("notes/a.md")
            assert flush_called.wait(timeout=3)

        assert len(captured_files) == 1
        assert captured_files[0] == ["notes/a.md"]

    def test_multiple_writes_batched_into_one_flush(self, batcher_fast: GitBatcher):
        flush_called = threading.Event()
        captured_files: list[list[str]] = []

        def mock_commit_and_pr(files: list[str]) -> None:
            captured_files.append(files)
            flush_called.set()

        with patch.object(batcher_fast, "_do_commit_and_pr", side_effect=mock_commit_and_pr):
            batcher_fast.enqueue("notes/a.md")
            time.sleep(0.2)
            batcher_fast.enqueue("notes/b.md")
            time.sleep(0.2)
            batcher_fast.enqueue("notes/c.md")
            assert flush_called.wait(timeout=3)

        assert len(captured_files) == 1
        assert captured_files[0] == ["notes/a.md", "notes/b.md", "notes/c.md"]

    def test_empty_pending_does_not_flush(self, batcher_fast: GitBatcher):
        flush_called = threading.Event()

        def mock_commit_and_pr(files: list[str]) -> None:
            flush_called.set()

        with patch.object(batcher_fast, "_do_commit_and_pr", side_effect=mock_commit_and_pr):
            batcher_fast._reset_timer()
            assert not flush_called.wait(timeout=2)


class TestDoCommitAndPR:
    def test_skips_when_nothing_to_commit(self, batcher_fast: GitBatcher):
        with patch("app.services.git_batcher.git_service") as gs, \
             patch("app.services.git_batcher.github_service"), \
             patch("app.services.git_batcher.SessionLocal") as sl:
            gs.current_branch.return_value = "main"
            gs.commit_for_batch.return_value = None
            mock_session = MagicMock()
            sl.return_value = mock_session

            batcher_fast._do_commit_and_pr(["notes/a.md"])

            gs.push_branch.assert_not_called()

    def test_calls_push_branch_and_ensure_pr_on_commit(self, batcher_fast: GitBatcher):
        with patch("app.services.git_batcher.git_service") as gs, \
             patch("app.services.git_batcher.github_service") as gh, \
             patch("app.services.git_batcher.SessionLocal") as sl:
            gs.current_branch.return_value = "main"
            gs.commit_for_batch.return_value = "abc123" + "0" * 34
            gh.ensure_pr.return_value = {"number": 42, "html_url": "https://github.com/test/pr/42"}
            mock_session = MagicMock()
            sl.return_value = mock_session

            batcher_fast._do_commit_and_pr(["notes/a.md"])

            gs.push_branch.assert_called_once()
            gh.ensure_pr.assert_called_once()

    def test_handles_push_failure(self, batcher_fast: GitBatcher):
        from app.services.git_service import GitError

        with patch("app.services.git_batcher.git_service") as gs, \
             patch("app.services.git_batcher.github_service"), \
             patch("app.services.git_batcher.SessionLocal") as sl:
            gs.current_branch.return_value = "main"
            gs.commit_for_batch.return_value = "abc123" + "0" * 34
            gs.GitError = GitError
            gs.push_branch.side_effect = GitError("push failed")
            mock_session = MagicMock()
            sl.return_value = mock_session

            batcher_fast._do_commit_and_pr(["notes/a.md"])

            add_calls = mock_session.add.call_args_list
            event_types = [
                c.args[0].event_type
                for c in add_calls
                if hasattr(c.args[0], "event_type")
            ]
            assert "git_push_failed" in event_types

    def test_handles_pr_creation_failure_gracefully(self, batcher_fast: GitBatcher):
        from app.services.github_service import GitHubError

        with patch("app.services.git_batcher.git_service") as gs, \
             patch("app.services.git_batcher.github_service") as gh, \
             patch("app.services.git_batcher.SessionLocal") as sl:
            gs.current_branch.return_value = "main"
            gs.commit_for_batch.return_value = "abc123" + "0" * 34
            gh.GitHubError = GitHubError
            gh.ensure_pr.side_effect = GitHubError("API error")
            mock_session = MagicMock()
            sl.return_value = mock_session

            batcher_fast._do_commit_and_pr(["notes/a.md"])

            add_calls = mock_session.add.call_args_list
            event_types = [
                c.args[0].event_type
                for c in add_calls
                if hasattr(c.args[0], "event_type")
            ]
            assert "pr_creation_failed" in event_types
            assert "git_push" in event_types
