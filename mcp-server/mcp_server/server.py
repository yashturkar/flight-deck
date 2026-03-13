from __future__ import annotations

from functools import wraps
from typing import Any
from urllib.parse import quote, unquote

from mcp.server.fastmcp import FastMCP

from mcp_server.client import KBServerClient, KBServerError
from mcp_server.config import MCPServerSettings


class FlightDeckMCPAdapter:
    def __init__(self, client: KBServerClient, settings: MCPServerSettings):
        self.client = client
        self.settings = settings

    def find_notes(
        self,
        query: str,
        limit: int | None = None,
        view: str | None = None,
    ) -> dict[str, Any]:
        return self.client.find_notes(
            query=query,
            view=view or self.settings.mcp_default_view,
            limit=limit or self.settings.mcp_default_limit,
        )

    def build_context_bundle(
        self,
        query: str,
        limit: int | None = None,
        token_budget: int | None = None,
        view: str | None = None,
    ) -> dict[str, Any]:
        return self.client.build_context_bundle(
            query=query,
            view=view or self.settings.mcp_default_view,
            limit=limit or self.settings.mcp_default_limit,
            token_budget=token_budget or self.settings.mcp_default_token_budget,
        )

    def list_notes(
        self,
        prefix: str = "",
        view: str | None = None,
    ) -> list[dict[str, Any]]:
        return self.client.list_notes(
            prefix=prefix,
            view=view or self.settings.mcp_default_view,
        )

    def read_note(self, path: str, view: str | None = None) -> dict[str, Any]:
        return self.client.read_note(path=path, view=view or self.settings.mcp_default_view)

    def read_note_resource(self, encoded_path: str, view: str) -> str:
        note = self.read_note(path=unquote(encoded_path), view=view)
        return note["content"]

    def write_note(self, path: str, content: str) -> dict[str, Any]:
        return self.client.write_note(path=path, content=content)

    def delete_note(self, path: str) -> dict[str, Any]:
        self.client.delete_note(path=path)
        return {"path": path, "deleted": True, "source": "api", "view": "main"}

    @staticmethod
    def encode_path(path: str) -> str:
        return quote(path, safe="")


def create_server(
    settings: MCPServerSettings | None = None,
    client: KBServerClient | None = None,
) -> FastMCP:
    settings = settings or MCPServerSettings()
    client = client or KBServerClient(
        base_url=settings.kb_server_url,
        api_key=settings.kb_api_key,
    )
    adapter = FlightDeckMCPAdapter(client=client, settings=settings)
    mcp = FastMCP("flight-deck", json_response=True)

    def _translate_errors(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except KBServerError as exc:
                raise RuntimeError(f"kb-server error ({exc.status_code}): {exc.detail}") from exc

        return wrapper

    @mcp.tool()
    @_translate_errors
    def find_notes(query: str, limit: int = 10, view: str | None = None) -> dict[str, Any]:
        """Find notes relevant to a topic or query."""
        return adapter.find_notes(query=query, limit=limit, view=view)

    @mcp.tool()
    @_translate_errors
    def build_context_bundle(
        query: str,
        limit: int = 10,
        token_budget: int | None = None,
        view: str | None = None,
    ) -> dict[str, Any]:
        """Return a bounded, ranked context bundle for a topic or query."""
        return adapter.build_context_bundle(
            query=query,
            limit=limit,
            token_budget=token_budget,
            view=view,
        )

    @mcp.tool()
    @_translate_errors
    def list_notes(prefix: str = "", view: str | None = None) -> list[dict[str, Any]]:
        """List notes under a prefix."""
        return adapter.list_notes(prefix=prefix, view=view)

    @mcp.tool()
    @_translate_errors
    def read_note(path: str, view: str | None = None) -> dict[str, Any]:
        """Read a note by path."""
        return adapter.read_note(path=path, view=view)

    @mcp.tool()
    @_translate_errors
    def write_note(path: str, content: str) -> dict[str, Any]:
        """Write a note through Flight Deck's API-origin workflow."""
        return adapter.write_note(path=path, content=content)

    @mcp.tool()
    @_translate_errors
    def delete_note(path: str) -> dict[str, Any]:
        """Delete a note through Flight Deck's API-origin workflow."""
        return adapter.delete_note(path=path)

    @mcp.resource("flightdeck://note/{view}/{encoded_path}")
    @_translate_errors
    def note_resource(view: str, encoded_path: str) -> str:
        """Read a note resource using a URL-encoded path."""
        return adapter.read_note_resource(encoded_path=encoded_path, view=view)

    return mcp


def main() -> None:
    settings = MCPServerSettings()
    server = create_server(settings=settings)
    server.run(transport=settings.mcp_transport)
