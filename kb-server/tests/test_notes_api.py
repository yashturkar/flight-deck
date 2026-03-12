"""Integration tests for the notes API routes."""

from __future__ import annotations

from tests.conftest import create_test_key


def _authed_client(app_client_factory, *, role: str = "user", name: str = "test-user"):
    client, session_factory = app_client_factory()
    with session_factory() as session:
        key = create_test_key(session, name, role)
    return client, {"X-API-Key": key}


class TestHealth:
    def test_health(self, app_client_factory):
        client, _ = app_client_factory()
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestNotesAPI:
    def test_write_and_read(self, app_client_factory):
        client, headers = _authed_client(app_client_factory)

        resp = client.put(
            "/notes/notes/test.md",
            json={"content": "# Test\n"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["path"] == "notes/test.md"
        assert resp.json()["content"] == "# Test\n"

        resp = client.get("/notes/notes/test.md", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["content"] == "# Test\n"

    def test_read_missing_note(self, app_client_factory):
        client, headers = _authed_client(app_client_factory)
        resp = client.get("/notes/notes/nope.md", headers=headers)
        assert resp.status_code == 404

    def test_write_bad_extension(self, app_client_factory):
        client, headers = _authed_client(app_client_factory)
        resp = client.put(
            "/notes/notes/bad.py",
            json={"content": "nope"},
            headers=headers,
        )
        assert resp.status_code == 400

    def test_write_bad_extension_detail(self, app_client_factory):
        client, headers = _authed_client(app_client_factory)
        resp = client.put(
            "/notes/notes/script.sh",
            json={"content": "nope"},
            headers=headers,
        )
        assert resp.status_code == 400
        assert "allow-list" in resp.json()["detail"]

    def test_list_notes(self, app_client_factory):
        client, headers = _authed_client(app_client_factory)

        client.put("/notes/notes/a.md", json={"content": "a"}, headers=headers)
        client.put("/notes/notes/b.md", json={"content": "b"}, headers=headers)

        resp = client.get("/notes/?prefix=notes", headers=headers)
        assert resp.status_code == 200
        paths = [item["path"] for item in resp.json()]
        assert "notes/a.md" in paths
        assert "notes/b.md" in paths

    def test_requires_authentication(self, app_client_factory):
        client, session_factory = app_client_factory()
        with session_factory() as session:
            create_test_key(session, "user-key", "user")

        resp = client.get("/notes/notes/hello.md")
        assert resp.status_code == 401

    def test_current_view_rejects_writes(self, app_client_factory):
        client, headers = _authed_client(app_client_factory)
        resp = client.put(
            "/notes/notes/test.md?view=current",
            json={"content": "# Test\n"},
            headers=headers,
        )
        assert resp.status_code == 400
        assert "read-only" in resp.json()["detail"]
