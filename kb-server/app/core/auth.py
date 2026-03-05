"""API-key authentication enforced on every request via middleware."""

from __future__ import annotations

import hmac
import logging

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings

log = logging.getLogger(__name__)


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Reject any request that does not carry a valid ``X-API-Key`` header.

    When ``KB_API_KEY`` is empty the middleware is a no-op so that local
    development without a key remains frictionless.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        expected = settings.kb_api_key
        if not expected:
            return await call_next(request)

        provided = request.headers.get("X-API-Key", "")
        if not provided or not hmac.compare_digest(provided, expected):
            log.warning(
                "rejected request %s %s — invalid or missing API key",
                request.method,
                request.url.path,
            )
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing API key"},
            )

        return await call_next(request)
