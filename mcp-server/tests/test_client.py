from __future__ import annotations

import json

import httpx
import pytest

from mcp_server.client import KBServerClient, KBServerError


def _json_response(payload: object, status_code: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        headers={"content-type": "application/json"},
        text=json.dumps(payload),
    )


def test_find_notes_calls_context_search():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return _json_response({"query": "mcp", "view": "current", "results": []})

    client = KBServerClient(
        base_url="http://fd.test",
        api_key="secret",
        transport=httpx.MockTransport(handler),
    )
    try:
        payload = client.find_notes("mcp", view="current", limit=5)
    finally:
        client.close()

    assert payload["view"] == "current"
    assert requests[0].method == "POST"
    assert requests[0].url.path == "/context/search"


def test_write_note_forces_api_origin():
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return _json_response({"path": "notes/x.md", "content": "body"})

    client = KBServerClient(
        base_url="http://fd.test",
        api_key="secret",
        transport=httpx.MockTransport(handler),
    )
    try:
        client.write_note("notes/x.md", "body")
    finally:
        client.close()

    assert "source=api" in str(captured[0].url)
    assert "view=main" in str(captured[0].url)


def test_errors_are_raised_with_status_and_detail():
    def handler(_: httpx.Request) -> httpx.Response:
        return _json_response({"detail": "Note not found"}, status_code=404)

    client = KBServerClient(
        base_url="http://fd.test",
        api_key="secret",
        transport=httpx.MockTransport(handler),
    )
    try:
        with pytest.raises(KBServerError) as exc_info:
            client.read_note("notes/missing.md", view="current")
    finally:
        client.close()

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Note not found"
