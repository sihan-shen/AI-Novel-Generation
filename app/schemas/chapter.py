from datetime import datetime
from pydantic import BaseModel


class ChapterCreate(BaseModel):
    project_id: str
    outline_id: str | None = None
    title: str
    content: str = ""
    sort_order: int = 0
    notes: str = ""


class ChapterUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    status: str | None = None
    notes: str | None = None
