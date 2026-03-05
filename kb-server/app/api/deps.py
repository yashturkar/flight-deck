import secrets

from fastapi import Header, HTTPException

from app.core.config import settings


def require_api_key(x_api_key: str = Header(alias="X-API-Key")) -> None:
    """Reject the request unless X-API-Key matches KB_API_KEY.

    When KB_API_KEY is blank the server is considered misconfigured for
    production use and all gated endpoints return 401.
    """
    configured = settings.kb_api_key
    if not configured:
        raise HTTPException(
            status_code=401,
            detail="API key not configured on server",
        )
    if not secrets.compare_digest(x_api_key, configured):
        raise HTTPException(status_code=401, detail="Invalid API key")
