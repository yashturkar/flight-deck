from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.models.db import VaultEvent, get_session
from app.schemas.notes import NoteContent, NoteListItem, NoteWrite
from app.services import vault_service
from app.services.revup_batcher import batcher

router = APIRouter(prefix="/notes", tags=["notes"])


@router.get("/", response_model=list[NoteListItem])
def list_notes(prefix: str = ""):
    items = vault_service.list_notes(prefix)
    return [NoteListItem(path=p, modified_at=mt) for p, mt in items]


@router.get("/{path:path}", response_model=NoteContent)
def read_note(path: str, session: Session = Depends(get_session)):
    try:
        content, modified_at = vault_service.read_note(path)
    except vault_service.PathNotAllowed as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except vault_service.NoteNotFound:
        raise HTTPException(status_code=404, detail="Note not found")

    session.add(VaultEvent(event_type="read", file_path=path))
    session.commit()

    return NoteContent(path=path, content=content, modified_at=modified_at)


@router.put("/{path:path}", response_model=NoteContent)
def write_note(
    path: str,
    body: NoteWrite,
    session: Session = Depends(get_session),
):
    try:
        modified_at = vault_service.write_note(path, body.content)
    except vault_service.PathNotAllowed as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    session.add(
        VaultEvent(
            event_type="write",
            file_path=path,
            details={"bytes": len(body.content)},
        )
    )
    session.commit()

    batcher.enqueue(path)

    return NoteContent(path=path, content=body.content, modified_at=modified_at)
