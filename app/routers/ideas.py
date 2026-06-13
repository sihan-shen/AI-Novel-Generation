from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.response import APIResponse
from app.services.idea_service import IdeaService


class IdeaResponse(BaseModel):
    id: str
    project_id: str | None
    title: str
    content: str
    source: str
    sort_order: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class IdeaCreate(BaseModel):
    project_id: str | None = None
    title: str = ""
    content: str = ""
    source: str = "手写"


router = APIRouter(prefix="/api/ideas", tags=["ideas"])


@router.get("", response_model=APIResponse[list[IdeaResponse]])
async def list_ideas(project_id: str | None = None, db: Session = Depends(get_db)):
    ideas = IdeaService.list_by_project(db, project_id)
    return APIResponse(data=ideas)


@router.post("", response_model=APIResponse[IdeaResponse], status_code=201)
async def create_idea(body: IdeaCreate, db: Session = Depends(get_db)):
    idea = IdeaService.create(
        db, project_id=body.project_id, title=body.title,
        content=body.content, source=body.source,
    )
    return APIResponse(data=idea)


@router.delete("/{idea_id}", response_model=APIResponse[dict])
async def delete_idea(idea_id: str, db: Session = Depends(get_db)):
    IdeaService.delete(db, idea_id)
    return APIResponse(data={"deleted": idea_id})


@router.post("/reorder", response_model=APIResponse[dict])
async def reorder_ideas(body: dict, db: Session = Depends(get_db)):
    IdeaService.reorder(db, body["items"])
    return APIResponse(data={"ok": True})
