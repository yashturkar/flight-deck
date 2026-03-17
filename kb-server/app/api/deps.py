"""FastAPI dependencies for authentication and authorization."""

from __future__ import annotations

from fastapi import HTTPException, Request

from app.core.identity import CallerIdentity


def get_caller(request: Request) -> CallerIdentity:
    """Return the authenticated caller identity set by the auth middleware.

    Raises 401 if the middleware did not attach an identity (should not
    happen for authenticated routes, but acts as a safety net).
    """
    identity: CallerIdentity | None = getattr(request.state, "identity", None)
    if identity is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return identity


def require_write(request: Request) -> CallerIdentity:
    """Like ``get_caller`` but also enforces write permission (403 for readonly)."""
    caller = get_caller(request)
    if not caller.can_write:
        raise HTTPException(
            status_code=403,
            detail="This API key does not have write permission",
        )
    return caller


# Deprecated alias — kept for any transient references
require_api_key = get_caller
