#!/usr/bin/env python3
"""Evaluate a target git ref in an isolated main-based worktree."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_API_KEY = "fd-eval-key"
DEFAULT_PORT = 8011


class HarnessError(RuntimeError):
    """Raised when the evaluation harness cannot proceed."""


@dataclass
class EvalPaths:
    temp_root: Path
    worktree_root: Path
    vault_root: Path
    sync_root: Path
    remote_root: Path
    db_path: Path
    logs_root: Path
    kb_env_file: Path
    sync_env_file: Path


@dataclass
class EvalContext:
    args: argparse.Namespace
    repo_root: Path
    paths: EvalPaths
    kb_python: Path
    vault_python: Path
    requested_target_ref: str
    resolved_target_ref: str
    base_ref: str
    changed_files: list[str]
    created_worktree: bool = False
    created_tmux_session: bool = False


def log(message: str) -> None:
    print(f"[eval_pr] {message}", flush=True)


def stage(message: str) -> None:
    log(f"==> {message}")


def run_command(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    log_path: Path | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
    rendered = " ".join(shlex.quote(part) for part in cmd)
    if cwd is not None:
        log(f"$ {rendered} (cwd={cwd})")
    else:
        log(f"$ {rendered}")

    process = subprocess.Popen(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    output_chunks: list[str] = []
    assert process.stdout is not None
    if log_path is None:
        sink = open(os.devnull, "w", encoding="utf-8")
    else:
        sink = log_path.open("w", encoding="utf-8")

    with sink:
        for line in process.stdout:
            sys.stdout.write(line)
            sink.write(line)
            output_chunks.append(line)
    returncode = process.wait()
    output = "".join(output_chunks)
    result = subprocess.CompletedProcess(cmd, returncode, output, "")
    if check and returncode != 0:
        raise HarnessError(f"command failed ({returncode}): {rendered}")
    return result


def run_git(repo_root: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=check,
    )
    return result.stdout.strip()


def ensure_binaries(repo_root: Path) -> tuple[Path, Path]:
    for binary in ("git", "tmux"):
        if shutil.which(binary) is None:
            raise HarnessError(f"required binary not found on PATH: {binary}")

    kb_python = repo_root / "kb-server" / ".venv" / "bin" / "python"
    vault_python = repo_root / "vault-sync" / ".venv" / "bin" / "python"
    missing = [str(path) for path in (kb_python, vault_python) if not path.exists()]
    if missing:
        raise HarnessError(
            "missing repo-local interpreters; expected:\n"
            + "\n".join(f"- {item}" for item in missing)
        )
    return kb_python, vault_python


def ensure_ref_exists(repo_root: Path, ref: str) -> None:
    try:
        run_git(repo_root, "rev-parse", "--verify", f"{ref}^{{commit}}")
    except subprocess.CalledProcessError as exc:
        raise HarnessError(f"git ref not found: {ref}") from exc


def resolve_ref_to_commit(repo_root: Path, ref: str) -> str:
    try:
        return run_git(repo_root, "rev-parse", "--verify", f"{ref}^{{commit}}")
    except subprocess.CalledProcessError as exc:
        raise HarnessError(f"git ref not found: {ref}") from exc


def create_paths() -> EvalPaths:
    temp_root = Path(tempfile.mkdtemp(prefix="fd-pr-eval-"))
    return EvalPaths(
        temp_root=temp_root,
        worktree_root=temp_root / "repo",
        vault_root=temp_root / "vault",
        sync_root=temp_root / "sync",
        remote_root=temp_root / "remote.git",
        db_path=temp_root / "kb-server.db",
        logs_root=temp_root / "logs",
        kb_env_file=temp_root / "kb-server.env",
        sync_env_file=temp_root / "vault-sync.env",
    )


def add_worktree(ctx: EvalContext) -> None:
    stage("Creating isolated worktree")
    run_command(
        ["git", "worktree", "add", "--detach", str(ctx.paths.worktree_root), ctx.base_ref],
        cwd=ctx.repo_root,
        log_path=ctx.paths.logs_root / "git-worktree-add.log",
    )
    ctx.created_worktree = True
    run_command(
        ["git", "checkout", "--detach", ctx.resolved_target_ref],
        cwd=ctx.paths.worktree_root,
        log_path=ctx.paths.logs_root / "git-checkout-target.log",
    )


def remove_worktree(repo_root: Path, worktree_root: Path) -> None:
    if not worktree_root.exists():
        return
    subprocess.run(
        ["git", "worktree", "remove", "--force", str(worktree_root)],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )


def collect_changed_files(worktree_root: Path, base_ref: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base_ref}...HEAD"],
        cwd=worktree_root,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def should_run_kb_tests(changed_files: list[str]) -> bool:
    if not changed_files:
        return True
    return any(path.startswith(("kb-server/", "scripts/")) for path in changed_files)


def should_run_vault_tests(changed_files: list[str]) -> bool:
    if not changed_files:
        return True
    return any(path.startswith(("vault-sync/", "scripts/")) for path in changed_files)


def should_run_e2e(changed_files: list[str]) -> bool:
    if not changed_files:
        return True
    return any(path.startswith(("kb-server/", "vault-sync/", "scripts/")) for path in changed_files)


def init_isolated_repos(paths: EvalPaths) -> None:
    stage("Creating isolated vault and remote")
    paths.vault_root.mkdir(parents=True, exist_ok=True)
    paths.sync_root.mkdir(parents=True, exist_ok=True)
    paths.logs_root.mkdir(parents=True, exist_ok=True)

    run_command(["git", "init", "--bare", str(paths.remote_root)], log_path=paths.logs_root / "git-init-remote.log")
    run_command(["git", "init", "-b", "main", str(paths.vault_root)], log_path=paths.logs_root / "git-init-vault.log")
    run_command(["git", "config", "user.email", "e2e@test.local"], cwd=paths.vault_root, log_path=paths.logs_root / "git-config-email.log")
    run_command(["git", "config", "user.name", "e2e-test"], cwd=paths.vault_root, log_path=paths.logs_root / "git-config-name.log")

    notes_dir = paths.vault_root / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    (notes_dir / "seed.md").write_text("# Seed\n", encoding="utf-8")

    run_command(["git", "add", "."], cwd=paths.vault_root, log_path=paths.logs_root / "git-seed-add.log")
    run_command(["git", "commit", "-m", "seed"], cwd=paths.vault_root, log_path=paths.logs_root / "git-seed-commit.log")
    run_command(["git", "remote", "add", "origin", str(paths.remote_root)], cwd=paths.vault_root, log_path=paths.logs_root / "git-add-remote.log")
    run_command(["git", "push", "-u", "origin", "main"], cwd=paths.vault_root, log_path=paths.logs_root / "git-push-main.log")


def write_env_file(path: Path, values: dict[str, str]) -> None:
    lines = [f"{key}={values[key]}" for key in sorted(values)]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_envs(ctx: EvalContext) -> tuple[dict[str, str], dict[str, str]]:
    kb_env = os.environ.copy()
    kb_env.update(
        {
            "VAULT_PATH": str(ctx.paths.vault_root),
            "DATABASE_URL": f"sqlite:///{ctx.paths.db_path}",
            "KB_API_KEY": DEFAULT_API_KEY,
            "GIT_REMOTE": "origin",
            "GIT_BRANCH": "main",
            "GIT_PUSH_ENABLED": "true",
            "AUTOSAVE_DEBOUNCE_SECONDS": "2",
            "GIT_PULL_INTERVAL_SECONDS": "30",
            "GIT_BATCH_DEBOUNCE_SECONDS": "2",
            "GIT_BATCH_BRANCH_PREFIX": "kb-api",
            "GITHUB_TOKEN": "",
            "GITHUB_REPO": "",
            "QUARTZ_BUILD_COMMAND": "",
            "QUARTZ_WEBHOOK_URL": "",
            "API_HOST": "127.0.0.1",
            "API_PORT": str(ctx.args.port),
        }
    )
    sync_env = os.environ.copy()
    sync_env.update(
        {
            "KB_SERVER_URL": f"http://127.0.0.1:{ctx.args.port}",
            "KB_API_KEY": DEFAULT_API_KEY,
            "SYNC_DIR": str(ctx.paths.sync_root),
            "SYNC_DEBOUNCE_SECONDS": "1",
            "SYNC_PULL_INTERVAL_SECONDS": "4",
        }
    )
    write_env_file(
        ctx.paths.kb_env_file,
        {key: kb_env[key] for key in (
            "API_HOST",
            "API_PORT",
            "AUTOSAVE_DEBOUNCE_SECONDS",
            "DATABASE_URL",
            "GIT_BATCH_BRANCH_PREFIX",
            "GIT_BATCH_DEBOUNCE_SECONDS",
            "GIT_BRANCH",
            "GIT_PULL_INTERVAL_SECONDS",
            "GIT_PUSH_ENABLED",
            "GIT_REMOTE",
            "GITHUB_REPO",
            "GITHUB_TOKEN",
            "KB_API_KEY",
            "QUARTZ_BUILD_COMMAND",
            "QUARTZ_WEBHOOK_URL",
            "VAULT_PATH",
        )},
    )
    write_env_file(
        ctx.paths.sync_env_file,
        {key: sync_env[key] for key in (
            "KB_API_KEY",
            "KB_SERVER_URL",
            "SYNC_DEBOUNCE_SECONDS",
            "SYNC_DIR",
            "SYNC_PULL_INTERVAL_SECONDS",
        )},
    )
    return kb_env, sync_env


def run_tests(ctx: EvalContext) -> None:
    if ctx.args.e2e_only:
        log("Skipping targeted tests due to --e2e-only")
        return

    if should_run_kb_tests(ctx.changed_files):
        stage("Running kb-server targeted tests")
        run_command(
            [
                str(ctx.kb_python),
                "-m",
                "pytest",
                "tests/test_current_view.py",
                "tests/test_source_and_delete.py",
                "-q",
            ],
            cwd=ctx.paths.worktree_root / "kb-server",
            log_path=ctx.paths.logs_root / "kb-server-tests.log",
        )
    else:
        log("Skipping kb-server targeted tests; no matching changes against main")

    if should_run_vault_tests(ctx.changed_files):
        stage("Running vault-sync targeted tests")
        run_command(
            [
                str(ctx.vault_python),
                "-m",
                "pytest",
                "tests/test_api_client.py",
                "tests/test_sync.py",
                "-q",
            ],
            cwd=ctx.paths.worktree_root / "vault-sync",
            log_path=ctx.paths.logs_root / "vault-sync-tests.log",
        )
    else:
        log("Skipping vault-sync targeted tests; no matching changes against main")


def run_migrations(ctx: EvalContext, kb_env: dict[str, str]) -> None:
    stage("Running kb-server migrations")
    run_command(
        [str(ctx.kb_python), "-m", "alembic", "upgrade", "head"],
        cwd=ctx.paths.worktree_root / "kb-server",
        env=kb_env,
        log_path=ctx.paths.logs_root / "kb-migrate.log",
    )


def tmux_has_session(name: str) -> bool:
    result = subprocess.run(
        ["tmux", "has-session", "-t", name],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def shell_from_env_file(workdir: Path, env_file: Path, command: list[str]) -> str:
    quoted_command = " ".join(shlex.quote(part) for part in command)
    return (
        f"cd {shlex.quote(str(workdir))} && "
        f"set -a && source {shlex.quote(str(env_file))} && set +a && "
        f"exec {quoted_command}"
    )


def start_server_tmux(ctx: EvalContext) -> None:
    session_name = ctx.args.tmux_session_name
    if tmux_has_session(session_name):
        raise HarnessError(f"tmux session already exists: {session_name}")

    stage(f"Starting tmux session {session_name}")
    server_cmd = shell_from_env_file(
        ctx.paths.worktree_root / "kb-server",
        ctx.paths.kb_env_file,
        [str(ctx.kb_python), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(ctx.args.port)],
    )
    run_command(["tmux", "new-session", "-d", "-s", session_name, server_cmd], log_path=ctx.paths.logs_root / "tmux-server.log")
    ctx.created_tmux_session = True
    run_command(
        [
            "tmux",
            "pipe-pane",
            "-o",
            "-t",
            f"{session_name}:0.0",
            f"cat >> {shlex.quote(str(ctx.paths.logs_root / 'server-pane.log'))}",
        ],
        log_path=ctx.paths.logs_root / "tmux-server-pipe.log",
    )


def start_sync_tmux(ctx: EvalContext) -> None:
    session_name = ctx.args.tmux_session_name
    sync_cmd = shell_from_env_file(
        ctx.paths.worktree_root / "vault-sync",
        ctx.paths.sync_env_file,
        [str(ctx.vault_python), "-m", "vault_sync.cli", "-v"],
    )
    run_command(["tmux", "split-window", "-h", "-t", session_name, sync_cmd], log_path=ctx.paths.logs_root / "tmux-sync.log")
    run_command(
        [
            "tmux",
            "pipe-pane",
            "-o",
            "-t",
            f"{session_name}:0.1",
            f"cat >> {shlex.quote(str(ctx.paths.logs_root / 'sync-pane.log'))}",
        ],
        log_path=ctx.paths.logs_root / "tmux-sync-pipe.log",
    )


def kill_tmux_session(name: str) -> None:
    if not tmux_has_session(name):
        return
    subprocess.run(["tmux", "kill-session", "-t", name], check=False, capture_output=True, text=True)


def request(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    body: dict[str, object] | None = None,
) -> tuple[int, str]:
    data = None
    req_headers = dict(headers or {})
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url=url, method=method, headers=req_headers, data=data)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")
    except urllib.error.URLError:
        return 0, ""


def wait_for_http(url: str, headers: dict[str, str], expected_status: int, timeout_seconds: float = 30.0) -> None:
    deadline = time.time() + timeout_seconds
    last_status = None
    while time.time() < deadline:
        status, _ = request("GET", url, headers=headers)
        last_status = status
        if status == expected_status:
            return
        time.sleep(0.5)
    raise HarnessError(f"timed out waiting for {url} to return {expected_status}; last_status={last_status}")


def git_output(vault_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=vault_root,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def expect_status(status: int, expected: int, context: str) -> None:
    if status != expected:
        raise HarnessError(f"{context}: expected HTTP {expected}, got {status}")


def run_e2e(ctx: EvalContext, kb_env: dict[str, str]) -> None:
    if ctx.args.tests_only:
        log("Skipping tmux-backed smoke flow due to --tests-only")
        return
    if not should_run_e2e(ctx.changed_files):
        log("Skipping tmux-backed smoke flow; no matching code changes against main")
        return

    run_migrations(ctx, kb_env)
    start_server_tmux(ctx)

    base_url = f"http://127.0.0.1:{ctx.args.port}"
    headers = {"X-API-Key": DEFAULT_API_KEY}
    wait_for_http(f"{base_url}/health", headers, 200)

    stage("Checking API key enforcement")
    status, _ = request("GET", f"{base_url}/health")
    expect_status(status, 401, "unauthorized health check")
    status, _ = request("GET", f"{base_url}/health", headers=headers)
    expect_status(status, 200, "authorized health check")

    stage("Checking source=human direct-to-main write")
    status, _ = request(
        "PUT",
        f"{base_url}/notes/notes/human-e2e.md?source=human",
        headers=headers,
        body={"content": "# Human\nmain write\n"},
    )
    expect_status(status, 200, "human write")
    subject = git_output(ctx.paths.vault_root, "log", "main", "-1", "--format=%s")
    if subject != "human: update notes/human-e2e.md":
        raise HarnessError(f"unexpected main commit after human write: {subject}")

    stage("Checking default API batching to kb-api/*")
    status, _ = request(
        "PUT",
        f"{base_url}/notes/notes/api-e2e.md",
        headers=headers,
        body={"content": "# API\npending branch write\n"},
    )
    expect_status(status, 200, "api write")
    time.sleep(4)

    status, _ = request("GET", f"{base_url}/notes/notes/api-e2e.md?view=main", headers=headers)
    expect_status(status, 404, "view=main after api batch write")
    status, _ = request("GET", f"{base_url}/notes/notes/api-e2e.md?view=current", headers=headers)
    expect_status(status, 200, "view=current after api batch write")

    branch_name = f"kb-api/{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
    branches = git_output(ctx.paths.vault_root, "branch", "--list", branch_name)
    if branch_name not in branches:
        raise HarnessError(f"expected local batch branch missing: {branch_name}")
    subject = git_output(ctx.paths.vault_root, "log", branch_name, "-1", "--format=%s")
    if "kb-api: update notes/api-e2e.md" not in subject:
        raise HarnessError(f"unexpected batch commit subject: {subject}")
    remote_heads = git_output(ctx.paths.vault_root, "ls-remote", "--heads", "origin", branch_name)
    if branch_name not in remote_heads:
        raise HarnessError(f"expected remote batch branch missing: {branch_name}")

    if ctx.args.no_sync:
        log("Skipping vault-sync smoke due to --no-sync")
        return

    stage("Checking vault-sync current-view pull and push flow")
    start_sync_tmux(ctx)
    deadline = time.time() + 20
    seed_path = ctx.paths.sync_root / "notes" / "seed.md"
    pending_path = ctx.paths.sync_root / "notes" / "api-e2e.md"
    while time.time() < deadline:
        if seed_path.exists() and pending_path.exists():
            break
        time.sleep(0.5)
    if not seed_path.exists() or not pending_path.exists():
        raise HarnessError("vault-sync did not complete initial pull of seed/current-view notes")

    sync_file = ctx.paths.sync_root / "notes" / "from-sync.md"
    sync_file.parent.mkdir(parents=True, exist_ok=True)
    sync_file.write_text("# From Sync\nclient write\n", encoding="utf-8")
    time.sleep(3)

    subject = git_output(ctx.paths.vault_root, "log", "main", "-1", "--format=%s")
    if subject != "human: update notes/from-sync.md":
        raise HarnessError(f"unexpected main commit after vault-sync push: {subject}")
    synced = git_output(ctx.paths.vault_root, "show", "main:notes/from-sync.md")
    if synced != "# From Sync\nclient write":
        raise HarnessError("vault-sync pushed unexpected file content")


def cleanup(ctx: EvalContext, success: bool) -> None:
    keep_temp = ctx.args.keep_temp or not success
    if keep_temp:
        log(f"Preserved temp root: {ctx.paths.temp_root}")
        if ctx.created_worktree:
            log(f"Preserved worktree: {ctx.paths.worktree_root}")
        if ctx.created_tmux_session:
            log(f"Preserved tmux session: {ctx.args.tmux_session_name}")
        return
    if ctx.created_tmux_session:
        kill_tmux_session(ctx.args.tmux_session_name)
    if ctx.created_worktree:
        remove_worktree(ctx.repo_root, ctx.paths.worktree_root)
    shutil.rmtree(ctx.paths.temp_root, ignore_errors=True)
    log("Removed temp worktree and runtime state")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate a target ref in an isolated main-based worktree.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """\
            Examples:
              python scripts/eval_pr.py origin/some-branch
              python scripts/eval_pr.py feature/foo --keep-temp
              python scripts/eval_pr.py HEAD --tests-only
            """
        ),
    )
    parser.add_argument("target_ref", help="Git ref to evaluate in the temp worktree.")
    parser.add_argument("--base-ref", default="main", help="Base branch for the temp worktree (default: main).")
    parser.add_argument("--keep-temp", action="store_true", help="Keep temp worktree, env files, and logs after success.")
    parser.add_argument("--no-sync", action="store_true", help="Skip the vault-sync pane and sync smoke checks.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"API port to use inside tmux (default: {DEFAULT_PORT}).")
    parser.add_argument(
        "--tmux-session-name",
        default=f"fd-pr-eval-{os.getpid()}",
        help="tmux session name for the isolated stack.",
    )
    parser.add_argument("--tests-only", action="store_true", help="Run targeted tests only; skip the tmux smoke flow.")
    parser.add_argument("--e2e-only", action="store_true", help="Run the tmux smoke flow only; skip targeted tests.")
    return parser


def print_summary(ctx: EvalContext) -> None:
    changed_preview = ", ".join(ctx.changed_files[:6]) if ctx.changed_files else "(no diff vs base)"
    if len(ctx.changed_files) > 6:
        changed_preview += ", ..."
    summary = textwrap.dedent(
        f"""\
        Evaluation summary
          base_ref:     {ctx.base_ref}
          target_ref:   {ctx.requested_target_ref}
          target_sha:   {ctx.resolved_target_ref}
          worktree:     {ctx.paths.worktree_root}
          temp_root:    {ctx.paths.temp_root}
          kb_python:    {ctx.kb_python}
          vault_python: {ctx.vault_python}
          changed:      {changed_preview}
          logs:         {ctx.paths.logs_root}
          tmux:         {ctx.args.tmux_session_name}
        """
    ).rstrip()
    print(summary)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.tests_only and args.e2e_only:
        parser.error("--tests-only and --e2e-only cannot be combined")

    kb_python, vault_python = ensure_binaries(REPO_ROOT)
    ensure_ref_exists(REPO_ROOT, args.base_ref)
    resolved_target_ref = resolve_ref_to_commit(REPO_ROOT, args.target_ref)

    ctx = EvalContext(
        args=args,
        repo_root=REPO_ROOT,
        paths=create_paths(),
        kb_python=kb_python,
        vault_python=vault_python,
        requested_target_ref=args.target_ref,
        resolved_target_ref=resolved_target_ref,
        base_ref=args.base_ref,
        changed_files=[],
    )

    success = False
    try:
        add_worktree(ctx)
        ctx.changed_files = collect_changed_files(ctx.paths.worktree_root, ctx.base_ref)
        print_summary(ctx)
        init_isolated_repos(ctx.paths)
        kb_env, _ = build_envs(ctx)
        run_tests(ctx)
        run_e2e(ctx, kb_env)
        success = True
        log("Evaluation completed successfully")
        return 0
    except HarnessError as exc:
        log(f"FAILED: {exc}")
        log(f"Inspect logs under: {ctx.paths.logs_root}")
        return 1
    finally:
        cleanup(ctx, success)


if __name__ == "__main__":
    sys.exit(main())
