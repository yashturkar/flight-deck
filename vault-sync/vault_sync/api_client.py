"""Thin HTTP client for the kb-server notes API."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from vault_sync.config import Settings

log = logging.getLogger(__name__)


class KBClient:
    """Wrapper around the kb-server REST API."""

    def __init__(self, settings: Settings | None = None) -> None:
        if settings is None:
            from vault_sync.config import settings as _settings
            settings = _settings
        self._base = settings.kb_server_url.rstrip("/")
        self._headers: dict[str, str] = {}
        if settings.kb_api_key:
            self._headers["X-API-Key"] = settings.kb_api_key
        self._timeout = 30.0

    def _url(self, path: str) -> str:
        return f"{self._base}/notes/{path}"

    def list_notes(
        self, *, view: str = "current", prefix: str = ""
    ) -> list[dict[str, Any]]:
        params: dict[str, str] = {"view": view}
        if prefix:
            params["prefix"] = prefix
        with httpx.Client(timeout=self._timeout) as c:
            resp = c.get(
                f"{self._base}/notes/",
                headers=self._headers,
                params=params,
            )
        resp.raise_for_status()
        return resp.json()

    def read_note(self, path: str, *, view: str = "current") -> dict[str, Any]:
        with httpx.Client(timeout=self._timeout) as c:
            resp = c.get(
                self._url(path),
                headers=self._headers,
                params={"view": view},
            )
        resp.raise_for_status()
        return resp.json()

    def write_note(self, path: str, content: str) -> dict[str, Any]:
        with httpx.Client(timeout=self._timeout) as c:
            resp = c.put(
                self._url(path),
                headers=self._headers,
                json={"content": content},
            )
        resp.raise_for_status()
        return resp.json()

    def delete_note(self, path: str) -> None:
        with httpx.Client(timeout=self._timeout) as c:
            resp = c.delete(
                self._url(path),
                headers=self._headers,
            )
        resp.raise_for_status()
