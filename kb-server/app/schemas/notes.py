from datetime import datetime

from pydantic import BaseModel


class NoteContent(BaseModel):
    path: str
    content: str
    modified_at: datetime
    view: str = "main"
    sources: list[str] | None = None


class NoteWrite(BaseModel):
    content: str


class NoteListItem(BaseModel):
    path: str
    modified_at: datetime
    view: str = "main"
    sources: list[str] | None = None


class PublishRequest(BaseModel):
    """Empty for now; may accept options later."""


class PublishResponse(BaseModel):
    run_id: int
    status: str
