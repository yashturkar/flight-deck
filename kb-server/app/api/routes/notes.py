from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import require_api_key
from app.core.config import settings
from app.models.db import VaultEvent, get_session
from app.schemas.notes import NoteContent, NoteListItem, NoteWrite
from app.services import current_view_service, git_service, vault_service
from app.services.git_batcher import batcher

router = APIRouter(
    prefix="/notes",
    tags=["notes"],
    dependencies=[Depends(require_api_key)],
)


class ViewType(str, Enum):
    main = "main"
    current = "current"


class SourceType(str, Enum):
    api = "api"
    human = "human"


@router.get("/", response_model=list[NoteListItem])
def list_notes(prefix: str = "", view: ViewType = Query(ViewType.main)):
    if view == ViewType.current:
        items = current_view_service.list_notes_current(prefix)
        return [
            NoteListItem(path=p, modified_at=mt, view="current", sources=src)
            for p, mt, src in items
        ]

    items = vault_service.list_notes(prefix)
    return [NoteListItem(path=p, modified_at=mt) for p, mt in items]


@router.get("/{path:path}", response_model=NoteContent)
def read_note(
    path: str,
    view: ViewType = Query(ViewType.main),
    session: Session = Depends(get_session),
):
    if view == ViewType.current:
        try:
            content, modified_at, sources = current_view_service.read_note_current(path)
        except vault_service.PathNotAllowed as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except vault_service.NoteNotFound:
            raise HTTPException(status_code=404, detail="Note not found")

        session.add(VaultEvent(event_type="read", file_path=path, details={"view": "current"}))
        session.commit()

        return NoteContent(
            path=path,
            content=content,
            modified_at=modified_at,
            view="current",
            sources=sources,
        )

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
    view: ViewType = Query(ViewType.main),
    source: SourceType = Query(SourceType.api),
    session: Session = Depends(get_session),
):
    if view == ViewType.current:
        raise HTTPException(
            status_code=400,
            detail="The 'current' view is read-only. Writes must target view=main.",
        )

    try:
        modified_at = vault_service.write_note(path, body.content)
    except vault_service.PathNotAllowed as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    session.add(
        VaultEvent(
            event_type="write",
            file_path=path,
            details={"bytes": len(body.content), "source": source.value},
        )
    )
    session.commit()

    if source == SourceType.human:
        git_service.commit_files([path], f"human: update {path}")
        if settings.git_push_enabled:
            git_service.push()
    else:
        batcher.enqueue(path)

    return NoteContent(path=path, content=body.content, modified_at=modified_at)


@router.delete("/{path:path}", status_code=204)
def delete_note(
    path: str,
    source: SourceType = Query(SourceType.api),
    session: Session = Depends(get_session),
):
    try:
        vault_service.delete_note(path)
    except vault_service.PathNotAllowed as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except vault_service.NoteNotFound:
        raise HTTPException(status_code=404, detail="Note not found")

    session.add(
        VaultEvent(
            event_type="delete",
            file_path=path,
            details={"source": source.value},
        )
    )
    session.commit()

    if source == SourceType.human:
        git_service.commit_files([path], f"human: delete {path}")
        if settings.git_push_enabled:
            git_service.push()
    else:
        batcher.enqueue(path)
