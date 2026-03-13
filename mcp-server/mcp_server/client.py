from __future__ import annotations

from typing import Any

import httpx


class KBServerError(RuntimeError):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class KBServerClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ):
        if not api_key:
            raise ValueError("KB_API_KEY must be configured")

        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"X-API-Key": api_key},
            timeout=timeout,
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def find_notes(self, query: str, *, view: str, limit: int) -> dict[str, Any]:
        return self._request(
            "POST",
            "/context/search",
            json={"query": query, "view": view, "limit": limit},
        )

    def build_context_bundle(
        self,
        query: str,
        *,
        view: str,
        limit: int,
        token_budget: int,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/context/bundle",
            json={
                "query": query,
                "view": view,
                "limit": limit,
                "token_budget": token_budget,
            },
        )

    def list_notes(self, *, prefix: str = "", view: str) -> list[dict[str, Any]]:
        return self._request(
            "GET",
            "/notes/",
            params={"prefix": prefix, "view": view},
        )

    def read_note(self, path: str, *, view: str) -> dict[str, Any]:
        return self._request(
            "GET",
            f"/notes/{path}",
            params={"view": view},
        )

    def write_note(self, path: str, content: str) -> dict[str, Any]:
        return self._request(
            "PUT",
            f"/notes/{path}",
            params={"view": "main", "source": "api"},
            json={"content": content},
        )

    def delete_note(self, path: str) -> None:
        self._request(
            "DELETE",
            f"/notes/{path}",
            params={"source": "api"},
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        try:
            response = self._client.request(method, path, params=params, json=json)
        except httpx.HTTPError as exc:
            raise KBServerError(502, f"kb-server request failed: {exc}") from exc

        if response.status_code >= 400:
            detail = _extract_detail(response)
            raise KBServerError(response.status_code, detail)

        if response.status_code == 204:
            return None
        return response.json()


def _extract_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text.strip() or f"kb-server returned {response.status_code}"
    if isinstance(payload, dict) and "detail" in payload:
        return str(payload["detail"])
    return str(payload)
