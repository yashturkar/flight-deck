from pathlib import Path
from unittest.mock import patch

import pytest

from app.services.vault_service import (
    NoteNotFound,
    PathNotAllowed,
    list_notes,
    read_note,
    safe_resolve,
    write_note,
)


@pytest.fixture(autouse=True)
def _patch_vault(tmp_vault: Path):
    with patch("app.services.vault_service.settings") as mock_settings:
        mock_settings.vault_path = tmp_vault
        yield


class TestSafeResolve:
    def test_simple_relative_path(self, tmp_vault: Path):
        result = safe_resolve("notes/hello.md")
        assert result == (tmp_vault / "notes" / "hello.md").resolve()

    def test_rejects_absolute_path(self):
        with pytest.raises(PathNotAllowed, match="Absolute"):
            safe_resolve("/etc/passwd")

    def test_rejects_dot_dot(self):
        with pytest.raises(PathNotAllowed, match="traversal"):
            safe_resolve("notes/../../../etc/passwd")

    def test_rejects_disallowed_extension(self):
        with pytest.raises(PathNotAllowed, match="allow-list"):
            safe_resolve("notes/script.py")

    def test_allows_txt(self, tmp_vault: Path):
        result = safe_resolve("notes/readme.txt")
        assert result.suffix == ".txt"


class TestReadWriteNote:
    def test_write_then_read(self):
        write_note("notes/test.md", "# Hello\n")
        content, mtime = read_note("notes/test.md")
        assert content == "# Hello\n"
        assert mtime is not None

    def test_read_missing_note(self):
        with pytest.raises(NoteNotFound):
            read_note("notes/does-not-exist.md")

    def test_write_creates_parent_dirs(self, tmp_vault: Path):
        write_note("deep/nested/dir/note.md", "content")
        assert (tmp_vault / "deep" / "nested" / "dir" / "note.md").is_file()


class TestListNotes:
    def test_list_empty(self):
        assert list_notes("nonexistent") == []

    def test_list_with_notes(self):
        write_note("notes/a.md", "a")
        write_note("notes/b.md", "b")
        write_note("notes/sub/c.md", "c")

        items = list_notes("notes")
        paths = [p for p, _ in items]
        assert "notes/a.md" in paths
        assert "notes/b.md" in paths
        assert "notes/sub/c.md" in paths

    def test_list_ignores_non_md(self, tmp_vault: Path):
        (tmp_vault / "notes").mkdir(exist_ok=True)
        (tmp_vault / "notes" / "image.png").write_bytes(b"fake")
        write_note("notes/real.md", "yes")

        items = list_notes("notes")
        paths = [p for p, _ in items]
        assert "notes/real.md" in paths
        assert "notes/image.png" not in paths
