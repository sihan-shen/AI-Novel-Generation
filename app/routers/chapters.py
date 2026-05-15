from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from pathlib import Path
from fastapi.templating import Jinja2Templates

from app.database import get_db
from app.schemas.chapter import ChapterCreate, ChapterUpdate
from app.services.chapter_service import ChapterService
from app.services.project_service import ProjectService

router = APIRouter(prefix="/project/{project_id}/writer", tags=["writer"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("", response_class=HTMLResponse)
async def writer_page(project_id: str, request: Request, db: Session = Depends(get_db)):
    project = ProjectService.get(db, project_id)
    if not project:
        return HTMLResponse("Not found", 404)
    chapters = ChapterService.list_by_project(db, project_id)
    return templates.TemplateResponse(request, "writer/index.html", {
        "project": project, "chapters": chapters,
    })


@router.get("/chapters")
async def chapter_list(project_id: str, request: Request, db: Session = Depends(get_db)):
    chapters = ChapterService.list_by_project(db, project_id)
    return templates.TemplateResponse(request, "writer/_sidebar.html", {"chapters": chapters, "project_id": project_id})


@router.get("/new")
async def new_chapter_form(project_id: str, request: Request):
    return templates.TemplateResponse(request, "writer/_form.html", {"project_id": project_id})


@router.post("/create")
async def create_chapter(request: Request, project_id: str, db: Session = Depends(get_db)):
    form = await request.form()
    data = ChapterCreate(project_id=project_id, title=str(form["title"]))
    ChapterService.create(db, data)
    chapters = ChapterService.list_by_project(db, project_id)
    return templates.TemplateResponse(request, "writer/_sidebar.html", {"chapters": chapters, "project_id": project_id})


@router.get("/{chapter_id}")
async def edit_chapter(chapter_id: str, request: Request, db: Session = Depends(get_db)):
    chapter = ChapterService.get(db, chapter_id)
    if not chapter:
        return HTMLResponse("Not found", 404)
    return templates.TemplateResponse(request, "writer/_editor.html", {"chapter": chapter})


@router.put("/{chapter_id}")
async def update_chapter(chapter_id: str, request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    data = ChapterUpdate(content=str(form.get("content", "")), title=str(form.get("title", "")))
    ChapterService.update(db, chapter_id, data)
    return HTMLResponse("ok")


@router.post("/reorder")
async def reorder_chapters(project_id: str, request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    ChapterService.reorder(db, data["items"])
    return HTMLResponse("ok")


@router.delete("/{chapter_id}")
async def delete_chapter(project_id: str, chapter_id: str, request: Request, db: Session = Depends(get_db)):
    ChapterService.delete(db, chapter_id)
    chapters = ChapterService.list_by_project(db, project_id)
    return templates.TemplateResponse(request, "writer/_sidebar.html", {"chapters": chapters, "project_id": project_id})
