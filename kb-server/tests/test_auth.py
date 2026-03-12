"""Tests for API-key authentication, identity resolution, and permissions."""

from __future__ import annotations

from datetime import datetime, timezone

from app.core.auth import _hash_key
from app.core.identity import CallerIdentity
from app.models.api_key import ApiKey
from tests.conftest import create_test_key


class TestMissingAndInvalidKeys:
    def test_missing_key_returns_401(self, app_client_factory):
        client, session_factory = app_client_factory()
        with session_factory() as session:
            create_test_key(session, "user-key", "user")

        resp = client.get("/notes/")
        assert resp.status_code == 401
        assert resp.json() == {"detail": "Missing API key"}

    def test_invalid_key_returns_401(self, app_client_factory):
        client, session_factory = app_client_factory()
        with session_factory() as session:
            create_test_key(session, "user-key", "user")

        resp = client.get("/notes/", headers={"X-API-Key": "kbk_invalid"})
        assert resp.status_code == 401
        assert resp.json() == {"detail": "Invalid API key"}


class TestRevocation:
    def test_revoked_key_returns_401(self, app_client_factory):
        client, session_factory = app_client_factory()
        with session_factory() as session:
            plaintext = create_test_key(session, "revoked", "user")
            row = session.query(ApiKey).filter(ApiKey.key_hash == _hash_key(plaintext)).one()
            row.is_active = False
            row.revoked_at = datetime.now(timezone.utc)
            session.commit()

        resp = client.get("/notes/", headers={"X-API-Key": plaintext})
        assert resp.status_code == 401
        assert resp.json() == {"detail": "Invalid API key"}


class TestIdentityResolution:
    def test_user_key_attaches_identity(self, app_client_factory):
        client, session_factory = app_client_factory(with_identity_route=True)
        with session_factory() as session:
            key = create_test_key(session, "yash-laptop", "user")

        resp = client.get("/__test/whoami", headers={"X-API-Key": key})
        assert resp.status_code == 200
        assert resp.json() == {
            "key_id": 1,
            "name": "yash-laptop",
            "role": "user",
            "prefix": key[:8],
            "actor": "user",
            "can_write": True,
        }

        with session_factory() as session:
            row = session.query(ApiKey).filter(ApiKey.prefix == key[:8]).one()
            assert row.last_used_at is not None

    def test_agent_key_attaches_identity(self, app_client_factory):
        client, session_factory = app_client_factory(with_identity_route=True)
        with session_factory() as session:
            key = create_test_key(session, "claude-agent", "agent")

        resp = client.get("/__test/whoami", headers={"X-API-Key": key})
        assert resp.status_code == 200
        assert resp.json() == {
            "key_id": 1,
            "name": "claude-agent",
            "role": "agent",
            "prefix": key[:8],
            "actor": "agent",
            "can_write": True,
        }


class TestReadonlyPermissions:
    def test_readonly_can_read(self, app_client_factory, tmp_vault):
        client, session_factory = app_client_factory()
        with session_factory() as session:
            key = create_test_key(session, "viewer", "readonly")

        (tmp_vault / "notes").mkdir(exist_ok=True)
        (tmp_vault / "notes" / "hello.md").write_text("hello", encoding="utf-8")

        resp = client.get("/notes/notes/hello.md", headers={"X-API-Key": key})
        assert resp.status_code == 200

    def test_readonly_put_returns_403(self, app_client_factory):
        client, session_factory = app_client_factory()
        with session_factory() as session:
            key = create_test_key(session, "viewer", "readonly")

        resp = client.put(
            "/notes/notes/test.md",
            json={"content": "blocked"},
            headers={"X-API-Key": key},
        )
        assert resp.status_code == 403

    def test_readonly_publish_returns_403(self, app_client_factory):
        client, session_factory = app_client_factory()
        with session_factory() as session:
            key = create_test_key(session, "viewer", "readonly")

        resp = client.post("/publish", headers={"X-API-Key": key})
        assert resp.status_code == 403


class TestLegacyFallback:
    def test_legacy_mode_works_when_db_has_no_keys(self, app_client_factory):
        client, _ = app_client_factory(
            legacy_key="legacy-secret",
            with_identity_route=True,
        )

        resp = client.get("/__test/whoami", headers={"X-API-Key": "legacy-secret"})
        assert resp.status_code == 200
        assert resp.json() == {
            "key_id": 0,
            "name": "legacy",
            "role": "admin",
            "prefix": "legacy",
            "actor": "user",
            "can_write": True,
        }

    def test_legacy_disabled_when_db_keys_exist(self, app_client_factory):
        client, session_factory = app_client_factory(legacy_key="legacy-secret")
        with session_factory() as session:
            create_test_key(session, "db-user", "user")

        resp = client.get("/notes/", headers={"X-API-Key": "legacy-secret"})
        assert resp.status_code == 401
        assert resp.json() == {"detail": "Invalid API key"}


class TestOpenHealthChecks:
    def test_health_is_accessible_without_auth(self, app_client_factory):
        client, _ = app_client_factory()
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_ready_is_accessible_without_auth(self, app_client_factory):
        client, _ = app_client_factory()
        resp = client.get("/ready")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ready"


class TestCallerIdentity:
    def test_identity_properties(self):
        user = CallerIdentity(key_id=1, name="laptop", role="user", prefix="kbk_abcd")
        assert user.actor == "user"
        assert user.can_write is True

        agent = CallerIdentity(key_id=2, name="bot", role="agent", prefix="kbk_efgh")
        assert agent.actor == "agent"
        assert agent.can_write is True

        readonly = CallerIdentity(
            key_id=3,
            name="viewer",
            role="readonly",
            prefix="kbk_view",
        )
        assert readonly.actor == "agent"
        assert readonly.can_write is False

        admin = CallerIdentity(key_id=4, name="admin", role="admin", prefix="legacy")
        assert admin.actor == "user"
        assert admin.can_write is True
