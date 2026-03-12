import os
from pathlib import Path

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite:///")
os.environ.setdefault("VAULT_PATH", "/tmp/kb-test-vault")


@pytest.fixture()
def tmp_vault(tmp_path: Path):
    """Create a temporary vault directory that is a git repo."""
    import subprocess

    vault = tmp_path / "vault"
    vault.mkdir()
    subprocess.run(["git", "init", "-b", "main", str(vault)], check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.local"],
        cwd=vault,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=vault,
        check=True,
        capture_output=True,
    )
    # Initial commit so HEAD exists
    (vault / ".gitkeep").touch()
    subprocess.run(["git", "add", "."], cwd=vault, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=vault,
        check=True,
        capture_output=True,
    )
    return vault


def create_test_key(session, name: str, role: str) -> str:
    """Insert a hashed API key and return the plaintext.

    Convenience helper for tests that need authenticated requests.
    """
    import secrets

    from app.core.auth import _hash_key
    from app.models.api_key import ApiKey

    plaintext = f"kbk_{secrets.token_hex(16)}"
    row = ApiKey(
        key_hash=_hash_key(plaintext),
        prefix=plaintext[:8],
        name=name,
        role=role,
    )
    session.add(row)
    session.commit()
    return plaintext


@pytest.fixture()
def app_client_factory(tmp_vault: Path, monkeypatch: pytest.MonkeyPatch):
    """Create a test app backed by an isolated in-memory SQLite database."""
    from app.core import auth as auth_module
    from app.core.config import settings
    from app.models import db as db_module
    from app.models.db import Base

    clients: list[tuple[TestClient, object]] = []

    def _factory(*, legacy_key: str = "", with_identity_route: bool = False):
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        session_factory = sessionmaker(bind=engine)
        Base.metadata.create_all(bind=engine)

        monkeypatch.setattr(db_module, "engine", engine)
        monkeypatch.setattr(db_module, "SessionLocal", session_factory)
        monkeypatch.setattr(auth_module, "SessionLocal", session_factory)

        monkeypatch.setattr(settings, "vault_path", tmp_vault, raising=False)
        monkeypatch.setattr(settings, "database_url", "sqlite://", raising=False)
        monkeypatch.setattr(settings, "kb_api_key", legacy_key, raising=False)
        monkeypatch.setattr(settings, "git_remote", "origin", raising=False)
        monkeypatch.setattr(settings, "git_branch", "main", raising=False)
        monkeypatch.setattr(settings, "git_push_enabled", False, raising=False)
        monkeypatch.setattr(
            settings, "git_batch_branch_prefix", "kb-api", raising=False
        )
        monkeypatch.setattr(settings, "github_repo", "", raising=False)
        monkeypatch.setattr(settings, "github_token", "", raising=False)
        monkeypatch.setattr(settings, "github_agent_token", "", raising=False)

        from app.main import create_app

        app = create_app()
        if with_identity_route:
            @app.get("/__test/whoami")
            def whoami(request: Request):
                identity = getattr(request.state, "identity", None)
                return {
                    "key_id": identity.key_id,
                    "name": identity.name,
                    "role": identity.role,
                    "prefix": identity.prefix,
                    "actor": identity.actor,
                    "can_write": identity.can_write,
                }

        client = TestClient(app)
        client.__enter__()
        clients.append((client, app))
        return client, session_factory

    yield _factory

    for client, app in clients:
        client.__exit__(None, None, None)
        app.dependency_overrides.clear()
