from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.models.db import get_session
from app.schemas.notes import PublishResponse
from app.services import git_service, publish_service

router = APIRouter(tags=["publish"])


@router.post("/publish", response_model=PublishResponse)
def publish(session: Session = Depends(get_session)):
    try:
        sha = git_service.current_sha()
    except git_service.GitError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    run = publish_service.trigger_publish(
        session,
        trigger="manual",
        commit_sha=sha,
    )
    if run is None:
        raise HTTPException(
            status_code=501,
            detail="Publishing is not configured",
        )

    return PublishResponse(run_id=run.id, status=run.status)
