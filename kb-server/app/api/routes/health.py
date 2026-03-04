from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.db import get_session

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/ready")
def ready(session: Session = Depends(get_session)):
    """Returns 200 only when both Postgres and the vault are reachable."""
    errors: list[str] = []

    try:
        session.execute(text("SELECT 1"))
    except Exception as exc:
        errors.append(f"db: {exc}")

    vault = settings.vault_path
    if not vault.is_dir():
        errors.append(f"vault directory missing: {vault}")
    if not (vault / ".git").is_dir():
        errors.append(f"vault is not a git repo: {vault}")

    if errors:
        return {"status": "not_ready", "errors": errors}
    return {"status": "ready"}
