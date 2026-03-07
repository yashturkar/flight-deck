"""Tests for KBClient using respx to mock HTTP calls."""

import pytest
import respx
from httpx import Response

from vault_sync.api_client import KBClient
from vault_sync.config import Settings


@pytest.fixture()
def client():
    s = Settings(kb_server_url="http://test-server:8000", kb_api_key="test-key")
    return KBClient(s)


BASE = "http://test-server:8000"


class TestListNotes:
    @respx.mock
    def test_returns_list(self, client: KBClient):
        respx.get(f"{BASE}/notes/").mock(
            return_value=Response(200, json=[
                {"path": "notes/a.md", "modified_at": "2026-03-06T00:00:00Z"},
            ])
        )
        result = client.list_notes(view="current")
        assert len(result) == 1
        assert result[0]["path"] == "notes/a.md"

    @respx.mock
    def test_sends_view_param(self, client: KBClient):
        route = respx.get(f"{BASE}/notes/").mock(
            return_value=Response(200, json=[])
        )
        client.list_notes(view="current", prefix="notes")
        assert route.called
        request = route.calls.last.request
        assert "view=current" in str(request.url)
        assert "prefix=notes" in str(request.url)


class TestReadNote:
    @respx.mock
    def test_returns_content(self, client: KBClient):
        respx.get(f"{BASE}/notes/notes/hello.md").mock(
            return_value=Response(200, json={
                "path": "notes/hello.md",
                "content": "# Hello\n",
                "modified_at": "2026-03-06T00:00:00Z",
            })
        )
        result = client.read_note("notes/hello.md", view="current")
        assert result["content"] == "# Hello\n"

    @respx.mock
    def test_sends_view_param(self, client: KBClient):
        route = respx.get(f"{BASE}/notes/notes/x.md").mock(
            return_value=Response(200, json={
                "path": "notes/x.md", "content": "", "modified_at": "2026-03-06T00:00:00Z",
            })
        )
        client.read_note("notes/x.md", view="main")
        assert "view=main" in str(route.calls.last.request.url)


class TestWriteNote:
    @respx.mock
    def test_sends_put_with_source(self, client: KBClient):
        route = respx.put(f"{BASE}/notes/notes/new.md").mock(
            return_value=Response(200, json={
                "path": "notes/new.md", "content": "body\n", "modified_at": "2026-03-06T00:00:00Z",
            })
        )
        result = client.write_note("notes/new.md", "body\n", source="human")
        assert route.called
        assert "source=human" in str(route.calls.last.request.url)
        assert result["content"] == "body\n"

    @respx.mock
    def test_sends_api_key_header(self, client: KBClient):
        route = respx.put(f"{BASE}/notes/notes/x.md").mock(
            return_value=Response(200, json={
                "path": "notes/x.md", "content": "", "modified_at": "2026-03-06T00:00:00Z",
            })
        )
        client.write_note("notes/x.md", "")
        assert route.calls.last.request.headers["X-API-Key"] == "test-key"


class TestDeleteNote:
    @respx.mock
    def test_sends_delete(self, client: KBClient):
        route = respx.delete(f"{BASE}/notes/notes/bye.md").mock(
            return_value=Response(204)
        )
        client.delete_note("notes/bye.md", source="human")
        assert route.called
        assert "source=human" in str(route.calls.last.request.url)
