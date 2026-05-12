from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from pathlib import Path
from fastapi.templating import Jinja2Templates

from app.database import get_db
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/list")
async def list_projects_html(request: Request, db: Session = Depends(get_db)):
    projects = ProjectService.list(db)
    return templates.TemplateResponse(request, "project/_list.html", {"projects": projects})


@router.get("/new")
async def new_project_form(request: Request):
    return templates.TemplateResponse(request, "project/_form.html", {})


@router.post("/create")
async def create_project(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    data = ProjectCreate(title=form["title"], description=form.get("description", ""), genre=form.get("genre", ""))
    ProjectService.create(db, data)
    projects = ProjectService.list(db)
    return templates.TemplateResponse(request, "project/_list.html", {"projects": projects})


@router.get("/{project_id}")
async def project_detail(request: Request, project_id: str, db: Session = Depends(get_db)):
    project = ProjectService.get(db, project_id)
    if not project:
        return HTMLResponse("Project not found", status_code=404)
    return templates.TemplateResponse(request, "project/detail.html", {"project": project})


@router.delete("/{project_id}")
async def delete_project(request: Request, project_id: str, db: Session = Depends(get_db)):
    ProjectService.delete(db, project_id)
    projects = ProjectService.list(db)
    return templates.TemplateResponse(request, "project/_list.html", {"projects": projects})
