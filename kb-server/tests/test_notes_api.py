"""Integration tests for the notes API routes.

Uses SQLite in-memory so no Postgres is required to run tests.
"""

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.db import Base, get_session

TEST_API_KEY = "test-secret-key-1234"


def _make_client(tmp_vault: Path, *, api_key: str = ""):
    """Build a TestClient with optional API key enforcement."""
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestSession = sessionmaker(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    def _override_session():
        s = TestSession()
        try:
            yield s
        finally:
            s.close()

    patches = [
        patch("app.services.vault_service.settings"),
        patch("app.services.git_service.settings"),
        patch("app.core.auth.settings"),
        patch("app.api.routes.notes.batcher"),
    ]
    mocks = [p.start() for p in patches]
    vs, gs, auth_s, _batcher_mock = mocks

    vs.vault_path = tmp_vault
    gs.vault_path = tmp_vault
    gs.git_remote = "origin"
    gs.git_branch = "main"
    auth_s.kb_api_key = api_key

    from app.main import create_app

    app = create_app()
    app.dependency_overrides[get_session] = _override_session

    client = TestClient(app)
    return client, app, patches


@pytest.fixture()
def client(tmp_vault: Path):
    """Client with auth disabled (no API key configured)."""
    c, app, patches = _make_client(tmp_vault, api_key="")
    yield c
    app.dependency_overrides.clear()
    for p in patches:
        p.stop()


@pytest.fixture()
def authed_client(tmp_vault: Path):
    """Client with auth enabled — must send X-API-Key."""
    c, app, patches = _make_client(tmp_vault, api_key=TEST_API_KEY)
    yield c
    app.dependency_overrides.clear()
    for p in patches:
        p.stop()


class TestAPIKeyAuth:
    """Verify that the API-key middleware gates every endpoint."""

    def test_no_key_returns_401(self, authed_client: TestClient):
        resp = authed_client.get("/health")
        assert resp.status_code == 401
        assert "API key" in resp.json()["detail"]

    def test_wrong_key_returns_401(self, authed_client: TestClient):
        resp = authed_client.get(
            "/health", headers={"X-API-Key": "wrong-key"}
        )
        assert resp.status_code == 401

    def test_correct_key_passes(self, authed_client: TestClient):
        resp = authed_client.get(
            "/health", headers={"X-API-Key": TEST_API_KEY}
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_notes_requires_key(self, authed_client: TestClient):
        resp = authed_client.get("/notes/notes/any.md")
        assert resp.status_code == 401

    def test_notes_with_key(self, authed_client: TestClient, tmp_vault: Path):
        (tmp_vault / "notes").mkdir(exist_ok=True)
        (tmp_vault / "notes" / "k.md").write_text("key ok")
        resp = authed_client.get(
            "/notes/notes/k.md", headers={"X-API-Key": TEST_API_KEY}
        )
        assert resp.status_code == 200

    def test_empty_key_config_disables_auth(self, client: TestClient):
        resp = client.get("/health")
        assert resp.status_code == 200


class TestHealth:
    def test_health(self, client: TestClient):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestNotesAPI:
    def test_write_and_read(self, client: TestClient):
        resp = client.put(
            "/notes/notes/test.md",
            json={"content": "# Test\n"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["path"] == "notes/test.md"
        assert data["content"] == "# Test\n"

        resp = client.get("/notes/notes/test.md")
        assert resp.status_code == 200
        assert resp.json()["content"] == "# Test\n"

    def test_read_missing_note(self, client: TestClient):
        resp = client.get("/notes/notes/nope.md")
        assert resp.status_code == 404

    def test_write_bad_extension(self, client: TestClient):
        resp = client.put(
            "/notes/notes/bad.py",
            json={"content": "nope"},
        )
        assert resp.status_code == 400

    def test_write_bad_extension_detail(self, client: TestClient):
        resp = client.put(
            "/notes/notes/script.sh",
            json={"content": "nope"},
        )
        assert resp.status_code == 400
        assert "allow-list" in resp.json()["detail"]

    def test_list_notes(self, client: TestClient):
        client.put("/notes/notes/a.md", json={"content": "a"})
        client.put("/notes/notes/b.md", json={"content": "b"})

        resp = client.get("/notes/?prefix=notes")
        assert resp.status_code == 200
        paths = [item["path"] for item in resp.json()]
        assert "notes/a.md" in paths
        assert "notes/b.md" in paths
