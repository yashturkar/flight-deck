from __future__ import annotations

from mcp_server.config import MCPServerSettings
from mcp_server.server import FlightDeckMCPAdapter, create_server


class DummyClient:
    def __init__(self):
        self.calls: list[tuple[str, tuple, dict]] = []

    def find_notes(self, query: str, *, view: str, limit: int):
        self.calls.append(("find_notes", (query,), {"view": view, "limit": limit}))
        return {"query": query, "view": view, "results": []}

    def build_context_bundle(self, query: str, *, view: str, limit: int, token_budget: int):
        self.calls.append(
            ("build_context_bundle", (query,), {"view": view, "limit": limit, "token_budget": token_budget})
        )
        return {"query": query, "view": view, "items": []}

    def list_notes(self, *, prefix: str, view: str):
        self.calls.append(("list_notes", (), {"prefix": prefix, "view": view}))
        return []

    def read_note(self, path: str, *, view: str):
        self.calls.append(("read_note", (path,), {"view": view}))
        return {"path": path, "content": "# Note"}

    def write_note(self, path: str, content: str):
        self.calls.append(("write_note", (path, content), {}))
        return {"path": path, "content": content}

    def delete_note(self, path: str):
        self.calls.append(("delete_note", (path,), {}))
        return None


def _settings() -> MCPServerSettings:
    return MCPServerSettings(
        kb_server_url="http://fd.test",
        kb_api_key="secret",
        mcp_default_view="current",
        mcp_default_limit=7,
        mcp_default_token_budget=321,
    )


def test_adapter_defaults_reads_to_current():
    client = DummyClient()
    adapter = FlightDeckMCPAdapter(client=client, settings=_settings())

    payload = adapter.find_notes("mcp")

    assert payload["view"] == "current"
    assert client.calls[0] == ("find_notes", ("mcp",), {"view": "current", "limit": 7})


def test_adapter_forces_api_origin_on_delete():
    client = DummyClient()
    adapter = FlightDeckMCPAdapter(client=client, settings=_settings())

    payload = adapter.delete_note("notes/x.md")

    assert payload == {"path": "notes/x.md", "deleted": True, "source": "api", "view": "main"}
    assert client.calls[0] == ("delete_note", ("notes/x.md",), {})


def test_note_resource_decodes_path():
    client = DummyClient()
    adapter = FlightDeckMCPAdapter(client=client, settings=_settings())

    content = adapter.read_note_resource("notes%2Ftest.md", "current")

    assert content == "# Note"
    assert client.calls[0] == ("read_note", ("notes/test.md",), {"view": "current"})


def test_server_construction_smoke():
    server = create_server(settings=_settings(), client=DummyClient())

    assert server is not None
