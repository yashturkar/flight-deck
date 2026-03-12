"""API-key authentication enforced on every request via middleware."""

from __future__ import annotations

import hashlib
import hmac
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings
from app.core.identity import CallerIdentity
from app.models.api_key import ApiKey
from app.models.db import SessionLocal

log = logging.getLogger(__name__)

_OPEN_PATHS = {"/health", "/ready"}
_LAST_USED_DEBOUNCE_SECONDS = 300


def _hash_key(plaintext: str) -> str:
    """Return a SHA-256 hex digest for a plaintext API key."""
    return hashlib.sha256(plaintext.encode()).hexdigest()


def _coerce_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Authenticate requests using DB-backed keys with legacy fallback."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.url.path in _OPEN_PATHS:
            return await call_next(request)

        provided = request.headers.get("X-API-Key", "")
        if not provided:
            return self._reject(request, "Missing API key")

        identity, has_db_keys = self._authenticate_db(provided)
        if identity is not None:
            request.state.identity = identity
            return await call_next(request)

        if not has_db_keys:
            legacy_identity = self._authenticate_legacy(provided)
            if legacy_identity is not None:
                request.state.identity = legacy_identity
                return await call_next(request)

        return self._reject(request, "Invalid API key")

    @staticmethod
    def _reject(request: Request, detail: str) -> JSONResponse:
        log.warning(
            "rejected request %s %s — %s",
            request.method,
            request.url.path,
            detail,
        )
        return JSONResponse(status_code=401, content={"detail": detail})

    @staticmethod
    def _authenticate_db(provided: str) -> tuple[CallerIdentity | None, bool]:
        """Return ``(identity, has_any_db_keys)`` for the provided plaintext key."""
        key_hash = _hash_key(provided)
        session = SessionLocal()
        try:
            has_any_keys = (
                session.execute(select(ApiKey.id).limit(1)).scalar_one_or_none()
                is not None
            )
            if not has_any_keys:
                return None, False

            row = session.execute(
                select(ApiKey).where(
                    ApiKey.key_hash == key_hash,
                    ApiKey.is_active.is_(True),
                    ApiKey.revoked_at.is_(None),
                )
            ).scalar_one_or_none()
            if row is None:
                return None, True

            now = datetime.now(timezone.utc)
            last_used_at = _coerce_utc(row.last_used_at)
            if (
                last_used_at is None
                or (now - last_used_at).total_seconds() > _LAST_USED_DEBOUNCE_SECONDS
            ):
                row.last_used_at = now
                session.commit()

            return _identity_from_row(row), True
        finally:
            session.close()

    @staticmethod
    def _authenticate_legacy(provided: str) -> CallerIdentity | None:
        """Authenticate with the deprecated single env-backed API key."""
        expected = settings.kb_api_key
        if not expected:
            return None

        if not hmac.compare_digest(provided, expected):
            return None

        log.warning(
            "DEPRECATION: authenticating via KB_API_KEY env var. "
            "Create database-backed API keys with "
            "'python -m app.cli.keys create' instead.",
        )
        return CallerIdentity(
            key_id=0,
            name="legacy",
            role="admin",
            prefix="legacy",
        )


def _identity_from_row(row: ApiKey) -> CallerIdentity:
    return CallerIdentity(
        key_id=row.id,
        name=row.name,
        role=row.role,
        prefix=row.prefix,
    )
