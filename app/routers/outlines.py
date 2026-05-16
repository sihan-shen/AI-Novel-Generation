from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from pathlib import Path
from fastapi.templating import Jinja2Templates

from app.database import get_db
from app.schemas.outline import OutlineCreate, OutlineUpdate
from app.services.outline_service import OutlineService
from app.services.project_service import ProjectService

router = APIRouter(prefix="/project/{project_id}/outline", tags=["outline"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("", response_class=HTMLResponse)
async def outline_page(project_id: str, request: Request, db: Session = Depends(get_db)):
    project = ProjectService.get(db, project_id)
    if not project:
        return HTMLResponse("Project not found", status_code=404)
    outlines = OutlineService.get_tree(db, project_id)
    return templates.TemplateResponse(request, "outline/index.html", {
        "project": project, "outlines": outlines
    })


@router.get("/tree")
async def outline_tree(project_id: str, request: Request, db: Session = Depends(get_db)):
    outlines = OutlineService.get_tree(db, project_id)
    return templates.TemplateResponse(request, "outline/_tree.html", {"outlines": outlines, "project_id": project_id})


@router.get("/new-item")
async def new_outline_form(project_id: str, request: Request, parent_id: str | None = None, level: int = 1, parent_title: str = "", db: Session = Depends(get_db)):
    if parent_id and not parent_title:
        parent = OutlineService.get(db, parent_id)
        parent_title = parent.title if parent else ""
    return templates.TemplateResponse(request, "outline/_form.html", {
        "project_id": project_id, "parent_id": parent_id, "level": level,
        "is_edit": False, "item": None, "post_url": f"/project/{project_id}/outline/create",
        "parent_title": parent_title,
    })


@router.post("/create")
async def create_outline(request: Request, project_id: str, db: Session = Depends(get_db)):
    form = await request.form()
    data = OutlineCreate(
        project_id=project_id,
        parent_id=form.get("parent_id") or None,
        level=int(form.get("level", 1)),
        title=form["title"],
        summary=form.get("summary", ""),
    )
    OutlineService.create(db, data)
    outlines = OutlineService.get_tree(db, project_id)
    return templates.TemplateResponse(request, "outline/_tree.html", {"outlines": outlines, "project_id": project_id})


@router.put("/{outline_id}")
async def update_outline(outline_id: str, request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    kwargs = {}
    for field in ("title", "summary", "notes", "status", "sort_order", "word_count_target", "pov_character"):
        if field in form:
            kwargs[field] = form[field]
    data = OutlineUpdate(**kwargs)
    OutlineService.update(db, outline_id, data)
    return HTMLResponse("ok")


@router.delete("/{outline_id}")
async def delete_outline(project_id: str, outline_id: str, request: Request, db: Session = Depends(get_db)):
    ok, child_count = OutlineService.delete(db, outline_id)
    if not ok:
        return HTMLResponse("Not found", status_code=404)
    outlines = OutlineService.get_tree(db, project_id)
    return templates.TemplateResponse(request, "outline/_tree.html", {"outlines": outlines, "project_id": project_id})


@router.post("/reorder")
async def reorder_outlines(project_id: str, request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    OutlineService.reorder(db, data["items"])
    return HTMLResponse("ok")
