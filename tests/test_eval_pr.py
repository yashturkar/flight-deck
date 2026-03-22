import argparse
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "eval_pr.py"
SPEC = importlib.util.spec_from_file_location("eval_pr", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
eval_pr = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = eval_pr
SPEC.loader.exec_module(eval_pr)


class EvalPrTests(unittest.TestCase):
    def make_context(self, temp_root: Path, *, keep_temp: bool = False) -> object:
        paths = eval_pr.EvalPaths(
            temp_root=temp_root,
            worktree_root=temp_root / "repo",
            vault_root=temp_root / "vault",
            sync_root=temp_root / "sync",
            remote_root=temp_root / "remote.git",
            db_path=temp_root / "kb.sqlite3",
            logs_root=temp_root / "logs",
            kb_env_file=temp_root / "kb.env",
            sync_env_file=temp_root / "sync.env",
        )
        return eval_pr.EvalContext(
            args=argparse.Namespace(
                keep_temp=keep_temp,
                tmux_session_name="fd-test-session",
            ),
            repo_root=temp_root,
            paths=paths,
            kb_python=Path("/tmp/kb-python"),
            vault_python=Path("/tmp/vault-python"),
            requested_target_ref="HEAD",
            resolved_target_ref="abc123",
            base_ref="main",
            changed_files=[],
        )

    def test_resolve_ref_to_commit_resolves_symbolic_head(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            subprocess.run(["git", "init"], cwd=repo_root, check=True, capture_output=True, text=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_root, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_root, check=True)
            (repo_root / "note.txt").write_text("hello\n", encoding="utf-8")
            subprocess.run(["git", "add", "note.txt"], cwd=repo_root, check=True)
            subprocess.run(["git", "commit", "-m", "init"], cwd=repo_root, check=True, capture_output=True, text=True)

            resolved = eval_pr.resolve_ref_to_commit(repo_root, "HEAD")
            expected = subprocess.run(
                ["git", "rev-parse", "--verify", "HEAD^{commit}"],
                cwd=repo_root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()

        self.assertEqual(resolved, expected)

    def test_add_worktree_checks_out_resolved_target_sha(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            ctx = self.make_context(Path(tmpdir))
            commands = []

            def fake_run_command(cmd, **kwargs):
                commands.append((cmd, kwargs))
                return None

            with mock.patch.object(eval_pr, "run_command", side_effect=fake_run_command):
                eval_pr.add_worktree(ctx)

        self.assertTrue(ctx.created_worktree)
        self.assertEqual(commands[0][0], ["git", "worktree", "add", "--detach", str(ctx.paths.worktree_root), "main"])
        self.assertEqual(commands[1][0], ["git", "checkout", "--detach", "abc123"])

    def test_cleanup_preserves_owned_resources_on_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            ctx = self.make_context(Path(tmpdir))
            ctx.created_worktree = True
            ctx.created_tmux_session = True

            with (
                mock.patch.object(eval_pr, "kill_tmux_session") as kill_tmux_session,
                mock.patch.object(eval_pr, "remove_worktree") as remove_worktree,
                mock.patch.object(eval_pr.shutil, "rmtree") as rmtree,
            ):
                eval_pr.cleanup(ctx, success=False)

        kill_tmux_session.assert_not_called()
        remove_worktree.assert_not_called()
        rmtree.assert_not_called()

    def test_cleanup_removes_only_owned_resources_on_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            ctx = self.make_context(Path(tmpdir))
            ctx.created_worktree = True
            ctx.created_tmux_session = False

            with (
                mock.patch.object(eval_pr, "kill_tmux_session") as kill_tmux_session,
                mock.patch.object(eval_pr, "remove_worktree") as remove_worktree,
                mock.patch.object(eval_pr.shutil, "rmtree") as rmtree,
            ):
                eval_pr.cleanup(ctx, success=True)

        kill_tmux_session.assert_not_called()
        remove_worktree.assert_called_once_with(ctx.repo_root, ctx.paths.worktree_root)
        rmtree.assert_called_once_with(ctx.paths.temp_root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
