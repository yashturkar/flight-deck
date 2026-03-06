"""Tests for pull_current and push_changes."""

from pathlib import Path
from unittest.mock import MagicMock, call

import pytest

from vault_sync.sync import pull_current, push_changes


@pytest.fixture()
def sync_dir(tmp_path: Path) -> Path:
    d = tmp_path / "sync"
    d.mkdir()
    return d


def _mock_client(notes: dict[str, str]) -> MagicMock:
    """Create a mock KBClient that serves *notes* (path -> content)."""
    client = MagicMock()
    client.list_notes.return_value = [
        {"path": p, "modified_at": "2026-03-06T00:00:00Z"} for p in notes
    ]
    client.read_note.side_effect = lambda path, **kw: {
        "path": path,
        "content": notes[path],
        "modified_at": "2026-03-06T00:00:00Z",
    }
    return client


class TestPullCurrent:
    def test_populates_empty_dir(self, sync_dir: Path):
        client = _mock_client({"notes/a.md": "alpha\n", "notes/b.md": "beta\n"})
        touched = pull_current(sync_dir, client)

        assert (sync_dir / "notes" / "a.md").read_text() == "alpha\n"
        assert (sync_dir / "notes" / "b.md").read_text() == "beta\n"
        assert touched == {"notes/a.md", "notes/b.md"}

    def test_skips_unchanged_files(self, sync_dir: Path):
        (sync_dir / "notes").mkdir(parents=True)
        (sync_dir / "notes" / "same.md").write_text("unchanged\n")

        client = _mock_client({"notes/same.md": "unchanged\n"})
        touched = pull_current(sync_dir, client)

        assert touched == set()

    def test_updates_changed_files(self, sync_dir: Path):
        (sync_dir / "notes").mkdir(parents=True)
        (sync_dir / "notes" / "doc.md").write_text("old\n")

        client = _mock_client({"notes/doc.md": "new\n"})
        touched = pull_current(sync_dir, client)

        assert (sync_dir / "notes" / "doc.md").read_text() == "new\n"
        assert "notes/doc.md" in touched

    def test_removes_deleted_files(self, sync_dir: Path):
        (sync_dir / "notes").mkdir(parents=True)
        (sync_dir / "notes" / "gone.md").write_text("bye\n")

        client = _mock_client({})
        touched = pull_current(sync_dir, client)

        assert not (sync_dir / "notes" / "gone.md").exists()
        assert "notes/gone.md" in touched

    def test_ignores_non_allowed_extensions(self, sync_dir: Path):
        (sync_dir / "notes").mkdir(parents=True)
        (sync_dir / "notes" / "keep.py").write_text("code\n")

        client = _mock_client({})
        pull_current(sync_dir, client)

        assert (sync_dir / "notes" / "keep.py").exists()

    def test_creates_parent_dirs(self, sync_dir: Path):
        client = _mock_client({"deep/nested/dir/note.md": "deep\n"})
        pull_current(sync_dir, client)
        assert (sync_dir / "deep" / "nested" / "dir" / "note.md").read_text() == "deep\n"


class TestPushChanges:
    def test_writes_changed_files(self, sync_dir: Path):
        (sync_dir / "notes").mkdir(parents=True)
        (sync_dir / "notes" / "edit.md").write_text("edited\n")

        client = MagicMock()
        client.write_note.return_value = {"path": "notes/edit.md", "content": "edited\n"}

        push_changes(sync_dir, {"notes/edit.md"}, set(), client)

        client.write_note.assert_called_once_with("notes/edit.md", "edited\n", source="human")

    def test_deletes_removed_files(self, sync_dir: Path):
        client = MagicMock()
        push_changes(sync_dir, set(), {"notes/gone.md"}, client)
        client.delete_note.assert_called_once_with("notes/gone.md", source="human")

    def test_skips_missing_changed_file(self, sync_dir: Path):
        client = MagicMock()
        push_changes(sync_dir, {"notes/phantom.md"}, set(), client)
        client.write_note.assert_not_called()

    def test_handles_write_error_gracefully(self, sync_dir: Path):
        (sync_dir / "notes").mkdir(parents=True)
        (sync_dir / "notes" / "err.md").write_text("content\n")

        client = MagicMock()
        client.write_note.side_effect = Exception("network error")

        push_changes(sync_dir, {"notes/err.md"}, set(), client)
