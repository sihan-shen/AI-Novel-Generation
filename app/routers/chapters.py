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


# ---- JSON API endpoints ----

from app.schemas.response import APIResponse
from fastapi import HTTPException
from pydantic import BaseModel
from datetime import datetime


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


api_router = APIRouter(prefix="/api/projects/{project_id}/chapters", tags=["chapters"])


@api_router.get("", response_model=APIResponse[list[ChapterResponse]])
async def api_list_chapters(project_id: str, db: Session = Depends(get_db)):
    chapters = ChapterService.list_by_project(db, project_id)
    return APIResponse(data=chapters)


@api_router.post("", response_model=APIResponse[ChapterResponse], status_code=201)
async def api_create_chapter(project_id: str, body: ChapterCreate, db: Session = Depends(get_db)):
    data = body.model_copy(update={"project_id": project_id})
    chapter = ChapterService.create(db, data)
    return APIResponse(data=chapter)


@api_router.get("/{chapter_id}", response_model=APIResponse[ChapterResponse])
async def api_get_chapter(chapter_id: str, project_id: str, db: Session = Depends(get_db)):
    chapter = ChapterService.get(db, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return APIResponse(data=chapter)


@api_router.put("/{chapter_id}", response_model=APIResponse[ChapterResponse])
async def api_update_chapter(chapter_id: str, project_id: str, body: ChapterUpdate, db: Session = Depends(get_db)):
    chapter = ChapterService.update(db, chapter_id, body)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return APIResponse(data=chapter)


@api_router.delete("/{chapter_id}", response_model=APIResponse[dict])
async def api_delete_chapter(chapter_id: str, project_id: str, db: Session = Depends(get_db)):
    ChapterService.delete(db, chapter_id)
    return APIResponse(data={"deleted": chapter_id})


@api_router.post("/reorder", response_model=APIResponse[dict])
async def api_reorder_chapters(project_id: str, body: dict, db: Session = Depends(get_db)):
    ChapterService.reorder(db, body["items"])
    return APIResponse(data={"ok": True})
