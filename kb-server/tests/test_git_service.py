import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from app.services.git_service import (
    build_revup_commit_message,
    commit,
    commit_for_revup,
    current_sha,
    has_changes,
    make_topic_name,
    push,
    stage_all,
)


@pytest.fixture(autouse=True)
def _patch_vault(tmp_vault: Path):
    with patch("app.services.git_service.settings") as mock_settings:
        mock_settings.vault_path = tmp_vault
        mock_settings.git_remote = "origin"
        mock_settings.git_branch = "main"
        mock_settings.revup_base_branch = "main"
        mock_settings.revup_topic_prefix = "kb-api"
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


class TestCurrentSha:
    def test_returns_40_char_hex(self):
        sha = current_sha()
        assert len(sha) == 40
        int(sha, 16)


class TestMakeTopicName:
    def test_single_file_includes_stem(self):
        topic = make_topic_name(["notes/hello.md"])
        assert topic.startswith("kb-api/")
        assert "hello" in topic

    def test_multiple_files_includes_batch_count(self):
        topic = make_topic_name(["a.md", "b.md", "c.md"])
        assert "batch-3" in topic

    def test_special_chars_sanitized(self):
        topic = make_topic_name(["notes/hello world!.md"])
        assert " " not in topic
        assert "!" not in topic


class TestBuildRevupCommitMessage:
    def test_basic_message_has_topic(self):
        msg = build_revup_commit_message("summary", "kb-api/my-topic")
        assert "Topic: kb-api/my-topic" in msg
        assert msg.startswith("summary")

    def test_relative_included(self):
        msg = build_revup_commit_message(
            "summary", "kb-api/t2", relative="kb-api/t1"
        )
        assert "Relative: kb-api/t1" in msg

    def test_no_relative_by_default(self):
        msg = build_revup_commit_message("s", "t")
        assert "Relative" not in msg


class TestCommitForRevup:
    def test_returns_sha_and_topic(self, tmp_vault: Path):
        (tmp_vault / "note.md").write_text("revup test")
        result = commit_for_revup(["note.md"])
        assert result is not None
        sha, topic = result
        assert len(sha) == 40
        assert topic.startswith("kb-api/")

    def test_returns_none_when_clean(self):
        assert commit_for_revup(["nothing.md"]) is None

    def test_commit_message_contains_topic_trailer(self, tmp_vault: Path):
        (tmp_vault / "note.md").write_text("content")
        sha, topic = commit_for_revup(["note.md"])
        result = subprocess.run(
            ["git", "log", "-1", "--format=%B"],
            cwd=tmp_vault,
            capture_output=True,
            text=True,
        )
        body = result.stdout.strip()
        assert f"Topic: {topic}" in body
