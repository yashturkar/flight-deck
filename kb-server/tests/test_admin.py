from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.auth import APIKeyMiddleware
from app.core.config import settings
from app.models.db import Base, Job, VaultEvent
from app.services import admin_service


def test_update_env_file_preserves_existing_content(tmp_path, monkeypatch):
    previous_vault = settings.vault_path
    previous_key = settings.kb_api_key
    previous_push_enabled = settings.git_push_enabled
    previous_api_port = settings.api_port
    previous_tmux_workdir = settings.admin_tmux_workdir
    previous_tmux_worker_session = settings.admin_tmux_worker_session
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# comment\nVAULT_PATH=/tmp/vault\nKB_API_KEY=old-key\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(admin_service, "ENV_FILE_PATH", env_file)

    try:
        result = admin_service.update_env_file(
            {
                "VAULT_PATH": "/srv/new-vault",
                "KB_API_KEY": "new-key",
                "GITHUB_REPO": "owner/repo",
                "GIT_PUSH_ENABLED": "false",
                "API_PORT": "9000",
                "ADMIN_TMUX_WORKDIR": "/srv/kb-server",
                "ADMIN_TMUX_WORKER_SESSION": "kb-worker-test",
            }
        )

        updated = env_file.read_text(encoding="utf-8")
        assert "# comment" in updated
        assert "VAULT_PATH=/srv/new-vault" in updated
        assert "KB_API_KEY=new-key" in updated
        assert "GITHUB_REPO=owner/repo" in updated
        assert "GIT_PUSH_ENABLED=false" in updated
        assert "API_PORT=9000" in updated
        assert "ADMIN_TMUX_WORKDIR=/srv/kb-server" in updated
        assert "ADMIN_TMUX_WORKER_SESSION=kb-worker-test" in updated
        assert result["restart_required"] is True

        assert settings.vault_path == Path("/srv/new-vault")
        assert settings.kb_api_key == "new-key"
        assert settings.git_push_enabled is False
        assert settings.api_port == 9000
        assert settings.admin_tmux_workdir == Path("/srv/kb-server")
        assert settings.admin_tmux_worker_session == "kb-worker-test"
    finally:
        settings.vault_path = previous_vault
        settings.kb_api_key = previous_key
        settings.git_push_enabled = previous_push_enabled
        settings.api_port = previous_api_port
        settings.admin_tmux_workdir = previous_tmux_workdir
        settings.admin_tmux_worker_session = previous_tmux_worker_session


def test_admin_state_hides_secret_values(monkeypatch, tmp_vault: Path):
    previous_vault = settings.vault_path
    previous_key = settings.kb_api_key
    try:
        settings.vault_path = tmp_vault
        settings.kb_api_key = "secret-key"
        monkeypatch.setattr(
            admin_service.github_service,
            "list_open_kb_api_prs",
            lambda: [],
        )
        env_file = tmp_vault.parent / ".env"
        env_file.write_text("KB_API_KEY=from-file\n", encoding="utf-8")
        monkeypatch.setattr(admin_service, "ENV_FILE_PATH", env_file)

        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        TestSession = sessionmaker(bind=engine)
        Base.metadata.create_all(bind=engine)

        with TestSession() as session:
            state = admin_service.system_state(session)
        config = admin_service.current_config_view()

        kb_key_rows = [row for row in config if row["key"] == "KB_API_KEY"]
        assert kb_key_rows[0]["value"] == ""
        assert kb_key_rows[0]["configured"] is True
        assert state["vault"]["exists"] is True
        assert state["vault"]["is_git_repo"] is True
    finally:
        settings.vault_path = previous_vault
        settings.kb_api_key = previous_key


def test_admin_state_exposes_autosave_summary(monkeypatch, tmp_vault: Path):
    previous_vault = settings.vault_path
    previous_key = settings.kb_api_key
    try:
        settings.vault_path = tmp_vault
        settings.kb_api_key = ""
        monkeypatch.setattr(
            admin_service.github_service,
            "list_open_kb_api_prs",
            lambda: [],
        )
        monkeypatch.setattr(
            admin_service,
            "_tmux_session_exists",
            lambda session_name: session_name == settings.admin_tmux_worker_session,
        )

        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        TestSession = sessionmaker(bind=engine)
        Base.metadata.create_all(bind=engine)

        with TestSession() as session:
            session.add(
                Job(
                    job_type="autosave",
                    status="completed",
                    meta={"files": ["notes/hello.md"]},
                )
            )
            session.add(
                VaultEvent(
                    event_type="autosave_commit",
                    commit_sha="abc123",
                )
            )
            session.add(
                VaultEvent(
                    event_type="autosave_push",
                    commit_sha="abc123",
                )
            )
            session.commit()

            state = admin_service.system_state(session)

        assert state["autosave"]["worker_session_running"] is True
        assert state["autosave"]["latest_job_status"] == "completed"
        assert state["autosave"]["latest_job_files"] == ["notes/hello.md"]
        assert state["autosave"]["latest_commit_sha"] == "abc123"
        assert state["autosave"]["latest_push_sha"] == "abc123"
    finally:
        settings.vault_path = previous_vault
        settings.kb_api_key = previous_key


async def test_admin_routes_bypass_api_key(monkeypatch, tmp_vault: Path):
    previous_key = settings.kb_api_key
    try:
        settings.kb_api_key = "secret-key"
        middleware = APIKeyMiddleware(app=lambda scope, receive, send: None)
        request = Request(
            {
                "type": "http",
                "method": "GET",
                "path": "/admin/api/state",
                "headers": [],
                "query_string": b"",
                "scheme": "http",
                "server": ("testserver", 80),
                "client": ("testclient", 123),
                "root_path": "",
                "http_version": "1.1",
            }
        )

        async def call_next(_request: Request):
            return JSONResponse({"ok": True})

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 200
    finally:
        settings.kb_api_key = previous_key


def test_runtime_control_state_uses_tmux_settings(tmp_path):
    previous_workdir = settings.admin_tmux_workdir
    previous_session = settings.admin_tmux_session
    previous_worker_session = settings.admin_tmux_worker_session
    previous_host = settings.api_host
    previous_port = settings.api_port
    try:
        settings.admin_tmux_workdir = tmp_path
        settings.admin_tmux_session = "kb-api-test"
        settings.admin_tmux_worker_session = "kb-worker-test"
        settings.api_host = "127.0.0.1"
        settings.api_port = 8123

        runtime = admin_service.runtime_control_state()
        api_runtime = runtime["api"]
        worker_runtime = runtime["worker"]

        assert api_runtime["tmux_session"] == "kb-api-test"
        assert api_runtime["workdir"] == str(tmp_path)
        assert "tmux new-session -d -s kb-api-test" in api_runtime["start_command"]
        assert "--host 127.0.0.1 --port 8123" in api_runtime["start_command"]
        assert "tmux respawn-pane -k -t kb-api-test:0.0" in api_runtime["restart_command"]
        assert worker_runtime["tmux_session"] == "kb-worker-test"
        assert worker_runtime["workdir"] == str(tmp_path)
        assert "tmux new-session -d -s kb-worker-test" in worker_runtime["start_command"]
        assert "python -m app.workers.autosave" in worker_runtime["start_command"]
        assert "tmux respawn-pane -k -t kb-worker-test:0.0" in worker_runtime["restart_command"]
    finally:
        settings.admin_tmux_workdir = previous_workdir
        settings.admin_tmux_session = previous_session
        settings.admin_tmux_worker_session = previous_worker_session
        settings.api_host = previous_host
        settings.api_port = previous_port
