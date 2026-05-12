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


@router.delete("/{idea_id}")
async def delete_idea(idea_id: str, db: Session = Depends(get_db)):
    IdeaService.delete(db, idea_id)
    return HTMLResponse("ok")
