from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from pathlib import Path
from fastapi.templating import Jinja2Templates

from app.database import get_db
from app.services.idea_service import IdeaService

router = APIRouter(prefix="/ideas", tags=["ideas"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("", response_class=HTMLResponse)
async def ideas_page(request: Request, db: Session = Depends(get_db)):
    ideas = IdeaService.list_by_project(db)
    return templates.TemplateResponse(request, "ideas/index.html", {"ideas": ideas})


@router.get("/list")
async def ideas_list(request: Request, project_id: str | None = None, db: Session = Depends(get_db)):
    ideas = IdeaService.list_by_project(db, project_id)
    return templates.TemplateResponse(request, "ideas/_list.html", {"ideas": ideas})


@router.post("/create")
async def create_idea(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    IdeaService.create(
        db,
        project_id=form.get("project_id") or None,
        title=form.get("title", ""),
        content=form.get("content", ""),
        source=form.get("source", "手写"),
    )
    ideas = IdeaService.list_by_project(db)
    return templates.TemplateResponse(request, "ideas/_list.html", {"ideas": ideas})


@router.post("/{idea_id}/promote")
async def promote_idea(idea_id: str, request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    IdeaService.promote(db, idea_id, form["target_type"], form.get("target_id", ""))
    return HTMLResponse("ok")


@router.post("/reorder")
async def reorder_ideas(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    IdeaService.reorder(db, data["items"])
    return HTMLResponse("ok")


@router.delete("/{idea_id}")
async def delete_idea(idea_id: str, request: Request, db: Session = Depends(get_db)):
    IdeaService.delete(db, idea_id)
    ideas = IdeaService.list_by_project(db)
    return templates.TemplateResponse(request, "ideas/_list.html", {"ideas": ideas})


# ---- JSON API endpoints ----

from app.schemas.response import APIResponse
from pydantic import BaseModel
from datetime import datetime


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


api_router = APIRouter(prefix="/api/ideas", tags=["ideas"])


@api_router.get("", response_model=APIResponse[list[IdeaResponse]])
async def api_list_ideas(project_id: str | None = None, db: Session = Depends(get_db)):
    ideas = IdeaService.list_by_project(db, project_id)
    return APIResponse(data=ideas)


@api_router.post("", response_model=APIResponse[IdeaResponse], status_code=201)
async def api_create_idea(body: IdeaCreate, db: Session = Depends(get_db)):
    idea = IdeaService.create(db, project_id=body.project_id, title=body.title,
                              content=body.content, source=body.source)
    return APIResponse(data=idea)


@api_router.delete("/{idea_id}", response_model=APIResponse[dict])
async def api_delete_idea(idea_id: str, db: Session = Depends(get_db)):
    IdeaService.delete(db, idea_id)
    return APIResponse(data={"deleted": idea_id})


@api_router.post("/reorder", response_model=APIResponse[dict])
async def api_reorder_ideas(body: dict, db: Session = Depends(get_db)):
    IdeaService.reorder(db, body["items"])
    return APIResponse(data={"ok": True})
