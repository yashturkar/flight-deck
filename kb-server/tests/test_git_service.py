import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from app.services.git_service import (
    GitError,
    _run,
    commit,
    commit_for_batch,
    current_sha,
    has_changes,
    push,
    stage_all,
)


@pytest.fixture(autouse=True)
def _patch_vault(tmp_vault: Path):
    with patch("app.services.git_service.settings") as mock_settings:
        mock_settings.vault_path = tmp_vault
        mock_settings.git_remote = "origin"
        mock_settings.git_branch = "main"
        yield


class TestHasChanges:
    def test_clean_repo_has_no_changes(self):
        assert has_changes() is False

    def test_new_file_shows_changes(self, tmp_vault: Path):
        (tmp_vault / "note.md").write_text("hello")
        assert has_changes() is True


class TestCommit:
    def test_commit_creates_sha(self, tmp_vault: Path):
        (tmp_vault / "note.md").write_text("hello")
        sha = commit("test commit")
        assert sha is not None
        assert len(sha) == 40

    def test_commit_returns_none_when_clean(self):
        sha = commit("nothing here")
        assert sha is None

    def test_commit_message_persisted(self, tmp_vault: Path):
        (tmp_vault / "note.md").write_text("hello")
        commit("my message")
        result = subprocess.run(
            ["git", "log", "-1", "--format=%s"],
            cwd=tmp_vault,
            capture_output=True,
            text=True,
        )
        assert result.stdout.strip() == "my message"


class TestPush:
    def test_push_fails_without_remote(self, tmp_vault: Path):
        (tmp_vault / "note.md").write_text("hello")
        commit("for push")

        from app.services.git_service import GitError

        with pytest.raises(GitError, match="push failed"):
            push(retries=1)


class TestRunAuthBehavior:
    def test_sets_non_interactive_git_env(self):
        with patch("app.services.git_service.subprocess.run") as run_mock:
            run_mock.return_value = subprocess.CompletedProcess(
                args=["git", "status"],
                returncode=0,
                stdout="",
                stderr="",
            )
            _run("status")
            _, kwargs = run_mock.call_args
            assert kwargs["env"]["GIT_TERMINAL_PROMPT"] == "0"
            assert kwargs["env"]["GCM_INTERACTIVE"] == "never"

    def test_auth_failure_adds_remediation_hint(self):
        with patch("app.services.git_service.subprocess.run") as run_mock:
            run_mock.return_value = subprocess.CompletedProcess(
                args=["git", "push", "origin", "main"],
                returncode=1,
                stdout="",
                stderr="remote: Invalid username or token.",
            )
            with pytest.raises(GitError, match="Configure non-interactive credentials"):
                _run("push", "origin", "main")


class TestCurrentSha:
    def test_returns_40_char_hex(self):
        sha = current_sha()
        assert len(sha) == 40
        int(sha, 16)


class TestCommitForBatch:
    def test_returns_sha(self, tmp_vault: Path):
        (tmp_vault / "note.md").write_text("batch test")
        sha = commit_for_batch(["note.md"])
        assert sha is not None
        assert len(sha) == 40

    def test_returns_none_when_clean(self):
        assert commit_for_batch(["nothing.md"]) is None

    def test_commit_message_is_plain_summary(self, tmp_vault: Path):
        (tmp_vault / "note.md").write_text("content")
        commit_for_batch(["note.md"])
        result = subprocess.run(
            ["git", "log", "-1", "--format=%s"],
            cwd=tmp_vault,
            capture_output=True,
            text=True,
        )
        subject = result.stdout.strip()
        assert subject.startswith("kb-api: update note")

    def test_tracks_deletions(self, tmp_vault: Path):
        (tmp_vault / "to_delete.md").write_text("will be deleted")
        commit_for_batch(["to_delete.md"])

        (tmp_vault / "to_delete.md").unlink()
        sha = commit_for_batch(["to_delete.md"])
        assert sha is not None

        result = subprocess.run(
            ["git", "show", "--name-status", "--format="],
            cwd=tmp_vault,
            capture_output=True,
            text=True,
        )
        assert "D\tto_delete.md" in result.stdout
