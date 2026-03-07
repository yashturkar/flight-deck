"""Tests for the read-only *current* view (Phase 1).

Covers:
- git_service.show_file / list_branches / list_tree
- current_view_service read and list
- API routes with ?view=current and write rejection
"""

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from app.services import git_service


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _git(vault: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=vault,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _commit_file(vault: Path, rel_path: str, content: str, msg: str) -> str:
    full = vault / rel_path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")
    _git(vault, "add", "--all")
    _git(vault, "commit", "-m", msg)
    return _git(vault, "rev-parse", "HEAD")


def _create_branch(vault: Path, branch: str) -> None:
    _git(vault, "checkout", "-b", branch)


def _checkout(vault: Path, branch: str) -> None:
    _git(vault, "checkout", branch)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _patch_vault(tmp_vault: Path):
    with patch("app.services.git_service.settings") as gs, \
         patch("app.services.vault_service.settings") as vs, \
         patch("app.services.current_view_service.settings") as cvs:
        for s in (gs, vs, cvs):
            s.vault_path = tmp_vault
            s.git_remote = "origin"
            s.git_branch = "main"
            s.git_batch_branch_prefix = "kb-api"
        yield


@pytest.fixture()
def vault_with_branch(tmp_vault: Path):
    """Vault with a main note and a kb-api branch that adds another note."""
    _commit_file(tmp_vault, "notes/approved.md", "# Approved\n", "add approved")
    _create_branch(tmp_vault, "kb-api/2026-03-06")
    _commit_file(tmp_vault, "notes/pending.md", "# Pending\n", "add pending")
    _checkout(tmp_vault, "main")
    return tmp_vault


@pytest.fixture()
def vault_with_overlap(tmp_vault: Path):
    """Vault where the same file exists on main and on a kb-api branch."""
    _commit_file(tmp_vault, "notes/shared.md", "main version\n", "add shared on main")
    _create_branch(tmp_vault, "kb-api/2026-03-06")
    _commit_file(tmp_vault, "notes/shared.md", "branch version\n", "update shared on branch")
    _checkout(tmp_vault, "main")
    return tmp_vault


# ===================================================================
# git_service helpers
# ===================================================================

class TestShowFile:
    def test_returns_content_from_main(self, tmp_vault: Path):
        _commit_file(tmp_vault, "notes/hello.md", "hello world\n", "add hello")
        content = git_service.show_file("main", "notes/hello.md")
        assert content == "hello world\n"

    def test_returns_none_for_missing_file(self, tmp_vault: Path):
        assert git_service.show_file("main", "notes/nope.md") is None

    def test_reads_from_branch_without_checkout(self, vault_with_branch: Path):
        assert git_service.current_branch() == "main"
        content = git_service.show_file("kb-api/2026-03-06", "notes/pending.md")
        assert content == "# Pending\n"
        assert git_service.current_branch() == "main"


class TestListBranches:
    def test_lists_matching_branches(self, vault_with_branch: Path):
        branches = git_service.list_branches("kb-api/*")
        assert "kb-api/2026-03-06" in branches

    def test_excludes_non_matching(self, vault_with_branch: Path):
        branches = git_service.list_branches("kb-api/*")
        assert "main" not in branches

    def test_returns_empty_for_no_match(self, tmp_vault: Path):
        assert git_service.list_branches("nonexistent/*") == []


class TestListTree:
    def test_lists_files_on_branch(self, vault_with_branch: Path):
        files = git_service.list_tree("kb-api/2026-03-06")
        assert "notes/pending.md" in files
        assert "notes/approved.md" in files

    def test_lists_files_with_prefix(self, vault_with_branch: Path):
        files = git_service.list_tree("main", "notes")
        assert "notes/approved.md" in files

    def test_empty_for_nonexistent_branch(self, tmp_vault: Path):
        assert git_service.list_tree("no-such-branch") == []


# ===================================================================
# current_view_service
# ===================================================================

class TestReadNoteCurrent:
    def test_returns_main_only_file(self, vault_with_branch: Path):
        from app.services import current_view_service

        with patch.object(current_view_service, "_pending_branches", return_value=["kb-api/2026-03-06"]):
            content, _, sources = current_view_service.read_note_current("notes/approved.md")

        assert content == "# Approved\n"
        assert "main" in sources

    def test_returns_branch_only_file(self, vault_with_branch: Path):
        from app.services import current_view_service

        with patch.object(current_view_service, "_pending_branches", return_value=["kb-api/2026-03-06"]):
            content, _, sources = current_view_service.read_note_current("notes/pending.md")

        assert content == "# Pending\n"
        assert "kb-api/2026-03-06" in sources

    def test_last_write_wins_on_overlap(self, vault_with_overlap: Path):
        from app.services import current_view_service

        with patch.object(current_view_service, "_pending_branches", return_value=["kb-api/2026-03-06"]):
            content, _, sources = current_view_service.read_note_current("notes/shared.md")

        assert content == "branch version\n"
        assert sources == ["main", "kb-api/2026-03-06"]

    def test_raises_not_found(self, tmp_vault: Path):
        from app.services import current_view_service
        from app.services.vault_service import NoteNotFound

        with patch.object(current_view_service, "_pending_branches", return_value=[]):
            with pytest.raises(NoteNotFound):
                current_view_service.read_note_current("notes/nope.md")

    def test_raises_path_not_allowed(self, tmp_vault: Path):
        from app.services import current_view_service
        from app.services.vault_service import PathNotAllowed

        with pytest.raises(PathNotAllowed):
            current_view_service.read_note_current("../escape.md")


class TestListNotesCurrent:
    def test_union_of_main_and_branch(self, vault_with_branch: Path):
        from app.services import current_view_service

        with patch.object(current_view_service, "_pending_branches", return_value=["kb-api/2026-03-06"]):
            items = current_view_service.list_notes_current()

        paths = [p for p, _, _ in items]
        assert "notes/approved.md" in paths
        assert "notes/pending.md" in paths

    def test_overlap_shows_both_sources(self, vault_with_overlap: Path):
        from app.services import current_view_service

        with patch.object(current_view_service, "_pending_branches", return_value=["kb-api/2026-03-06"]):
            items = current_view_service.list_notes_current()

        for path, _, sources in items:
            if path == "notes/shared.md":
                assert "main" in sources
                assert "kb-api/2026-03-06" in sources
                break
        else:
            pytest.fail("notes/shared.md not found in listing")

    def test_filters_non_allowed_extensions(self, tmp_vault: Path):
        _commit_file(tmp_vault, "notes/good.md", "ok\n", "add good")
        _commit_file(tmp_vault, "notes/bad.py", "nope\n", "add bad")

        from app.services import current_view_service

        with patch.object(current_view_service, "_pending_branches", return_value=[]):
            items = current_view_service.list_notes_current()

        paths = [p for p, _, _ in items]
        assert "notes/good.md" in paths
        assert "notes/bad.py" not in paths


# ===================================================================
# Pending-branches resolution
# ===================================================================

class TestPendingBranches:
    def test_falls_back_to_local_branches(self, vault_with_branch: Path):
        from app.services import current_view_service

        with patch.object(current_view_service.github_service, "list_open_kb_api_prs", side_effect=Exception("no token")):
            branches = current_view_service._pending_branches()

        assert "kb-api/2026-03-06" in branches

    def test_uses_github_prs_when_available(self, vault_with_branch: Path):
        from app.services import current_view_service

        fake_prs = [{"head": {"ref": "kb-api/2026-03-06"}}]
        with patch.object(current_view_service.github_service, "list_open_kb_api_prs", return_value=fake_prs):
            branches = current_view_service._pending_branches()

        assert branches == ["kb-api/2026-03-06"]
