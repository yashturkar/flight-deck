"""Tests for source=human direct-to-main writes and DELETE endpoint."""

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from app.services import git_service, vault_service


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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _patch_vault(tmp_vault: Path):
    with patch("app.services.git_service.settings") as gs, \
         patch("app.services.vault_service.settings") as vs, \
         patch("app.core.config.settings") as cfg:
        for s in (gs, vs, cfg):
            s.vault_path = tmp_vault
            s.git_remote = "origin"
            s.git_branch = "main"
            s.git_push_enabled = False
            s.git_batch_branch_prefix = "kb-api"
        yield


# ===================================================================
# vault_service.delete_note
# ===================================================================

class TestVaultDeleteNote:
    def test_deletes_existing_file(self, tmp_vault: Path):
        (tmp_vault / "notes").mkdir(exist_ok=True)
        (tmp_vault / "notes" / "bye.md").write_text("gone\n")
        vault_service.delete_note("notes/bye.md")
        assert not (tmp_vault / "notes" / "bye.md").exists()

    def test_raises_not_found(self, tmp_vault: Path):
        with pytest.raises(vault_service.NoteNotFound):
            vault_service.delete_note("notes/nope.md")

    def test_raises_path_not_allowed(self, tmp_vault: Path):
        with pytest.raises(vault_service.PathNotAllowed):
            vault_service.delete_note("../escape.md")


# ===================================================================
# git_service: commit_files stages deletions
# ===================================================================

class TestCommitFilesDeletion:
    def test_stages_and_commits_deletion(self, tmp_vault: Path):
        _commit_file(tmp_vault, "notes/del.md", "to delete\n", "add file")
        (tmp_vault / "notes" / "del.md").unlink()

        sha = git_service.commit_files(["notes/del.md"], "delete it")
        assert sha is not None

        log_output = _git(tmp_vault, "log", "-1", "--name-status", "--format=")
        assert "D\tnotes/del.md" in log_output


# ===================================================================
# source=human write (direct to main)
# ===================================================================

class TestSourceHumanWrite:
    def test_commits_directly_to_main(self, tmp_vault: Path):
        (tmp_vault / "notes").mkdir(exist_ok=True)
        (tmp_vault / "notes" / "existing.md").write_text("old\n")
        _git(tmp_vault, "add", "--all")
        _git(tmp_vault, "commit", "-m", "seed")

        vault_service.write_note("notes/existing.md", "updated by human\n")
        sha = git_service.commit_files(
            ["notes/existing.md"], "human: update notes/existing.md"
        )
        assert sha is not None

        log_msg = _git(tmp_vault, "log", "-1", "--format=%s")
        assert log_msg.startswith("human:")

        branch = git_service.current_branch()
        assert branch == "main"

    def test_creates_new_file_on_main(self, tmp_vault: Path):
        vault_service.write_note("notes/brand-new.md", "# Fresh\n")
        sha = git_service.commit_files(
            ["notes/brand-new.md"], "human: update notes/brand-new.md"
        )
        assert sha is not None
        assert (tmp_vault / "notes" / "brand-new.md").read_text() == "# Fresh\n"

    def test_default_source_does_not_commit(self, tmp_vault: Path):
        old_sha = git_service.current_sha()
        vault_service.write_note("notes/api-note.md", "api content\n")
        new_sha = git_service.current_sha()
        assert old_sha == new_sha


# ===================================================================
# DELETE flow
# ===================================================================

class TestDeleteFlow:
    def test_delete_and_commit(self, tmp_vault: Path):
        _commit_file(tmp_vault, "notes/remove-me.md", "bye\n", "add file")
        assert (tmp_vault / "notes" / "remove-me.md").exists()

        vault_service.delete_note("notes/remove-me.md")
        sha = git_service.commit_files(
            ["notes/remove-me.md"], "human: delete notes/remove-me.md"
        )
        assert sha is not None
        assert not (tmp_vault / "notes" / "remove-me.md").exists()

        log_output = _git(tmp_vault, "log", "-1", "--name-status", "--format=")
        assert "D\tnotes/remove-me.md" in log_output
