from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.auth import APIKeyMiddleware
from app.core.config import settings
from app.models.db import Base
from app.services import admin_service


def test_update_env_file_preserves_existing_content(tmp_path, monkeypatch):
    previous_vault = settings.vault_path
    previous_key = settings.kb_api_key
    previous_push_enabled = settings.git_push_enabled
    previous_api_port = settings.api_port
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
            }
        )

        updated = env_file.read_text(encoding="utf-8")
        assert "# comment" in updated
        assert "VAULT_PATH=/srv/new-vault" in updated
        assert "KB_API_KEY=new-key" in updated
        assert "GITHUB_REPO=owner/repo" in updated
        assert "GIT_PUSH_ENABLED=false" in updated
        assert "API_PORT=9000" in updated
        assert result["restart_required"] is True

        assert settings.vault_path == Path("/srv/new-vault")
        assert settings.kb_api_key == "new-key"
        assert settings.git_push_enabled is False
        assert settings.api_port == 9000
    finally:
        settings.vault_path = previous_vault
        settings.kb_api_key = previous_key
        settings.git_push_enabled = previous_push_enabled
        settings.api_port = previous_api_port


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
