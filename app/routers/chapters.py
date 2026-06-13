from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.chapter import ChapterCreate, ChapterUpdate
from app.schemas.response import APIResponse
from app.services.chapter_service import ChapterService


class ChapterResponse(BaseModel):
    id: str
    project_id: str
    outline_id: str | None
    title: str
    content: str
    status: str
    sort_order: int
    notes: str
    word_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


router = APIRouter(prefix="/api/projects/{project_id}/chapters", tags=["chapters"])


@router.get("", response_model=APIResponse[list[ChapterResponse]])
async def list_chapters(project_id: str, db: Session = Depends(get_db)):
    chapters = ChapterService.list_by_project(db, project_id)
    return APIResponse(data=chapters)


@router.post("", response_model=APIResponse[ChapterResponse], status_code=201)
async def create_chapter(project_id: str, body: ChapterCreate, db: Session = Depends(get_db)):
    data = body.model_copy(update={"project_id": project_id})
    chapter = ChapterService.create(db, data)
    return APIResponse(data=chapter)


@router.get("/{chapter_id}", response_model=APIResponse[ChapterResponse])
async def get_chapter(chapter_id: str, project_id: str, db: Session = Depends(get_db)):
    chapter = ChapterService.get(db, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return APIResponse(data=chapter)


@router.put("/{chapter_id}", response_model=APIResponse[ChapterResponse])
async def update_chapter(chapter_id: str, project_id: str, body: ChapterUpdate, db: Session = Depends(get_db)):
    chapter = ChapterService.update(db, chapter_id, body)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return APIResponse(data=chapter)


@router.delete("/{chapter_id}", response_model=APIResponse[dict])
async def delete_chapter(chapter_id: str, project_id: str, db: Session = Depends(get_db)):
    ChapterService.delete(db, chapter_id)
    return APIResponse(data={"deleted": chapter_id})


@router.post("/reorder", response_model=APIResponse[dict])
async def reorder_chapters(project_id: str, body: dict, db: Session = Depends(get_db)):
    ChapterService.reorder(db, body["items"])
    return APIResponse(data={"ok": True})
