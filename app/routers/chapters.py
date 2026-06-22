import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.chapter_snapshot import ChapterSnapshot
from app.schemas.chapter import ChapterCreate, ChapterUpdate
from app.schemas.response import APIResponse
from app.services.chapter_service import ChapterService

logger = logging.getLogger(__name__)


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

    model_config = ConfigDict(from_attributes=True)


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
async def update_chapter(chapter_id: str, project_id: str, body: ChapterUpdate, db: Session = Depends(get_db)):  # noqa: E501
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


@router.post("/{chapter_id}/rollback", response_model=APIResponse[dict])
async def rollback_chapter(chapter_id: str, project_id: str, task_id: str = Query(...), db: Session = Depends(get_db)):  # noqa: E501
    chapter = ChapterService.get(db, chapter_id)
    if not chapter or chapter.project_id != project_id:
        raise HTTPException(status_code=404, detail="Chapter not found")

    snapshot = (
        db.query(ChapterSnapshot)
        .filter(ChapterSnapshot.chapter_id == chapter_id, ChapterSnapshot.task_id == task_id)
        .order_by(ChapterSnapshot.created_at.desc())
        .first()
    )
    if not snapshot:
        raise HTTPException(status_code=404, detail="No snapshot found for this chapter+task")

    chapter.content = snapshot.content
    chapter.title = snapshot.title
    db.commit()
    return APIResponse(data={"status": "restored", "chapter_id": chapter_id})

logger.info("Module %s loaded", __name__)
