from __future__ import annotations

import os
import re
import shlex
import subprocess
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import Settings, settings
from app.models.db import Job, PublishRun, VaultEvent
from app.services import git_service, github_service
from app.services.git_batcher import batcher

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE_PATH = PROJECT_ROOT / ".env"

VISIBLE_CONFIG_KEYS = (
    "VAULT_PATH",
    "DATABASE_URL",
    "GIT_REMOTE",
    "GIT_BRANCH",
    "GIT_PUSH_ENABLED",
    "GIT_BATCH_DEBOUNCE_SECONDS",
    "GIT_BATCH_BRANCH_PREFIX",
    "GITHUB_REPO",
    "AUTOSAVE_DEBOUNCE_SECONDS",
    "GIT_PULL_INTERVAL_SECONDS",
    "QUARTZ_BUILD_COMMAND",
    "QUARTZ_WEBHOOK_URL",
    "ADMIN_TMUX_SESSION",
    "ADMIN_TMUX_WORKER_SESSION",
    "ADMIN_TMUX_WORKDIR",
    "API_HOST",
    "API_PORT",
)
SECRET_CONFIG_KEYS = ("KB_API_KEY", "GITHUB_TOKEN")
CONFIG_KEY_PATTERN = re.compile(r"^\s*([A-Z0-9_]+)\s*=(.*)$")


def _load_env_file_map() -> dict[str, str]:
    if not ENV_FILE_PATH.exists():
        return {}

    values: dict[str, str] = {}
    for line in ENV_FILE_PATH.read_text(encoding="utf-8").splitlines():
        match = CONFIG_KEY_PATTERN.match(line)
        if not match:
            continue
        key, value = match.groups()
        values[key] = value.strip()
    return values


def _stringify(value: Any) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    return str(value)


def _setting_value(key: str) -> str:
    attr = key.lower()
    value = getattr(settings, attr)
    return _stringify(value)


def _coerce_setting_value(key: str, value: str) -> Any:
    field = Settings.model_fields[key.lower()]
    annotation = field.annotation

    if annotation is Path:
        return Path(value)
    if annotation is bool:
        return value.strip().lower() in {"1", "true", "yes", "on"}
    if annotation is int:
        return int(value)
    return value


def _value_source(key: str, env_file_values: dict[str, str]) -> str:
    if key in os.environ:
        return "environment"
    if key in env_file_values:
        return ".env"
    return "default"


def current_config_view() -> list[dict[str, Any]]:
    env_file_values = _load_env_file_map()

    rows = [
        {
            "key": key,
            "value": _setting_value(key),
            "source": _value_source(key, env_file_values),
            "secret": False,
        }
        for key in VISIBLE_CONFIG_KEYS
    ]

    for key in SECRET_CONFIG_KEYS:
        rows.append(
            {
                "key": key,
                "value": "",
                "source": _value_source(key, env_file_values),
                "secret": True,
                "configured": bool(getattr(settings, key.lower())),
            }
        )

    return rows


def update_env_file(updates: dict[str, str]) -> dict[str, Any]:
    ENV_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing_lines = []
    if ENV_FILE_PATH.exists():
        existing_lines = ENV_FILE_PATH.read_text(encoding="utf-8").splitlines()

    pending = {key: value for key, value in updates.items() if value is not None}
    written_keys: list[str] = []
    new_lines: list[str] = []

    for line in existing_lines:
        match = CONFIG_KEY_PATTERN.match(line)
        if not match:
            new_lines.append(line)
            continue

        key = match.group(1)
        if key not in pending:
            new_lines.append(line)
            continue

        new_lines.append(f"{key}={pending[key]}")
        written_keys.append(key)
        del pending[key]

    for key, value in pending.items():
        if new_lines and new_lines[-1] != "":
            new_lines.append("")
        new_lines.append(f"{key}={value}")
        written_keys.append(key)

    ENV_FILE_PATH.write_text("\n".join(new_lines).rstrip() + "\n", encoding="utf-8")

    for key, value in updates.items():
        if value is None:
            continue
        setattr(settings, key.lower(), _coerce_setting_value(key, value))

    return {
        "written_keys": written_keys,
        "env_file": str(ENV_FILE_PATH),
        "restart_required": True,
    }


def launch_command(command: str) -> None:
    subprocess.Popen(
        command,
        shell=True,
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _tmux_session_exists(session_name: str) -> bool | None:
    try:
        result = subprocess.run(
            ["tmux", "has-session", "-t", session_name],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        return None
    return result.returncode == 0


def _tmux_api_command() -> str:
    workdir = settings.admin_tmux_workdir
    return (
        f"cd {shlex.quote(str(workdir))} && "
        "source .venv/bin/activate && "
        f"python -m uvicorn app.main:app --host {settings.api_host} --port {settings.api_port}"
    )


def _tmux_worker_command() -> str:
    workdir = settings.admin_tmux_workdir
    return (
        f"cd {shlex.quote(str(workdir))} && "
        "source .venv/bin/activate && "
        "python -m app.workers.autosave"
    )


def _tmux_process_state(session_name: str, command: str) -> dict[str, Any]:
    workdir = settings.admin_tmux_workdir
    venv_python = workdir / ".venv" / "bin" / "python"
    return {
        "tmux_session": session_name,
        "session_running": _tmux_session_exists(session_name),
        "workdir": str(workdir),
        "workdir_exists": workdir.is_dir(),
        "venv_python_exists": venv_python.exists(),
        "start_command": (
            f"tmux new-session -d -s {shlex.quote(session_name)} '{command}'"
        ),
        "restart_command": (
            f"tmux respawn-pane -k -t {shlex.quote(session_name)}:0.0 '{command}'"
        ),
    }


def runtime_control_state() -> dict[str, Any]:
    return {
        "api": _tmux_process_state(settings.admin_tmux_session, _tmux_api_command()),
        "worker": _tmux_process_state(settings.admin_tmux_worker_session, _tmux_worker_command()),
    }


def backend_start_command() -> str:
    return runtime_control_state()["api"]["start_command"]


def backend_restart_command() -> str:
    return runtime_control_state()["api"]["restart_command"]


def worker_start_command() -> str:
    return runtime_control_state()["worker"]["start_command"]


def worker_restart_command() -> str:
    return runtime_control_state()["worker"]["restart_command"]


def system_state(session: Session) -> dict[str, Any]:
    ready_errors: list[str] = []
    runtime = runtime_control_state()

    try:
        session.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as exc:
        db_status = "error"
        ready_errors.append(f"db: {exc}")

    vault_path = settings.vault_path
    vault_exists = vault_path.is_dir()
    vault_is_git = (vault_path / ".git").is_dir()
    if not vault_exists:
        ready_errors.append(f"vault directory missing: {vault_path}")
    elif not vault_is_git:
        ready_errors.append(f"vault is not a git repo: {vault_path}")

    git_summary: dict[str, Any]
    try:
        git_summary = {
            "branch": git_service.current_branch(),
            "has_changes": git_service.has_changes(),
            "current_sha": git_service.current_sha(),
        }
    except Exception as exc:
        git_summary = {"error": str(exc)}

    pr_summary: dict[str, Any]
    try:
        prs = github_service.list_open_kb_api_prs()
        pr_summary = {
            "count": len(prs),
            "items": [
                {
                    "number": pr.get("number"),
                    "title": pr.get("title"),
                    "url": pr.get("html_url"),
                    "head": pr.get("head", {}).get("ref"),
                }
                for pr in prs[:10]
            ],
        }
    except Exception as exc:
        pr_summary = {"error": str(exc), "count": 0, "items": []}

    jobs = (
        session.query(Job)
        .order_by(Job.created_at.desc())
        .limit(10)
        .all()
    )
    events = (
        session.query(VaultEvent)
        .order_by(VaultEvent.created_at.desc())
        .limit(10)
        .all()
    )
    publish_runs = (
        session.query(PublishRun)
        .order_by(PublishRun.started_at.desc())
        .limit(10)
        .all()
    )
    latest_autosave_job = (
        session.query(Job)
        .filter(Job.job_type == "autosave")
        .order_by(Job.created_at.desc())
        .first()
    )
    latest_autosave_commit = (
        session.query(VaultEvent)
        .filter(VaultEvent.event_type == "autosave_commit")
        .order_by(VaultEvent.created_at.desc())
        .first()
    )
    latest_autosave_push = (
        session.query(VaultEvent)
        .filter(VaultEvent.event_type == "autosave_push")
        .order_by(VaultEvent.created_at.desc())
        .first()
    )

    return {
        "ready": not ready_errors,
        "ready_errors": ready_errors,
        "vault": {
            "path": str(vault_path),
            "exists": vault_exists,
            "is_git_repo": vault_is_git,
        },
        "database": {"status": db_status},
        "git": git_summary,
        "prs": pr_summary,
        "batcher": {
            "pending_count": batcher.pending_count(),
            "pending_paths": batcher.pending_paths(),
        },
        "runtime": runtime,
        "autosave": {
            "worker_session_running": runtime["worker"]["session_running"],
            "latest_job_status": latest_autosave_job.status if latest_autosave_job else None,
            "latest_job_created_at": latest_autosave_job.created_at.isoformat() if latest_autosave_job and latest_autosave_job.created_at else None,
            "latest_job_completed_at": latest_autosave_job.completed_at.isoformat() if latest_autosave_job and latest_autosave_job.completed_at else None,
            "latest_job_error": latest_autosave_job.error if latest_autosave_job else None,
            "latest_job_files": (
                latest_autosave_job.meta.get("files", [])
                if latest_autosave_job and isinstance(latest_autosave_job.meta, dict)
                else []
            ),
            "latest_commit_sha": latest_autosave_commit.commit_sha if latest_autosave_commit else None,
            "latest_commit_at": latest_autosave_commit.created_at.isoformat() if latest_autosave_commit and latest_autosave_commit.created_at else None,
            "latest_push_sha": latest_autosave_push.commit_sha if latest_autosave_push else None,
            "latest_push_at": latest_autosave_push.created_at.isoformat() if latest_autosave_push and latest_autosave_push.created_at else None,
        },
        "jobs": [
            {
                "id": job.id,
                "type": job.job_type,
                "status": job.status,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "error": job.error,
            }
            for job in jobs
        ],
        "events": [
            {
                "id": event.id,
                "type": event.event_type,
                "file_path": event.file_path,
                "commit_sha": event.commit_sha,
                "created_at": event.created_at.isoformat() if event.created_at else None,
            }
            for event in events
        ],
        "publish_runs": [
            {
                "id": run.id,
                "trigger": run.trigger,
                "status": run.status,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                "error": run.error,
            }
            for run in publish_runs
        ],
    }
