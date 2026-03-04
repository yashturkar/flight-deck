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


@pytest.fixture()
def client(tmp_vault: Path):
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

    with patch("app.services.vault_service.settings") as vs, \
         patch("app.services.git_service.settings") as gs:
        vs.vault_path = tmp_vault
        gs.vault_path = tmp_vault
        gs.git_remote = "origin"
        gs.git_branch = "main"

        from app.main import create_app

        app = create_app()
        app.dependency_overrides[get_session] = _override_session
        yield TestClient(app)
        app.dependency_overrides.clear()


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
