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


# ---- JSON API endpoints ----

from app.schemas.response import APIResponse
from app.schemas.project import ProjectResponse, ProjectCreate as ProjectCreateSchema
from fastapi import HTTPException

api_router = APIRouter(prefix="/api/projects", tags=["projects"])


@api_router.get("", response_model=APIResponse[list[ProjectResponse]])
async def api_list_projects(db: Session = Depends(get_db)):
    projects = ProjectService.list(db)
    return APIResponse(data=projects)


@api_router.post("", response_model=APIResponse[ProjectResponse], status_code=201)
async def api_create_project(body: ProjectCreateSchema, db: Session = Depends(get_db)):
    project = ProjectService.create(db, body)
    return APIResponse(data=project)


@api_router.get("/{project_id}", response_model=APIResponse[ProjectResponse])
async def api_get_project(project_id: str, db: Session = Depends(get_db)):
    project = ProjectService.get(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return APIResponse(data=project)


@api_router.delete("/{project_id}", response_model=APIResponse[dict])
async def api_delete_project(project_id: str, db: Session = Depends(get_db)):
    ProjectService.delete(db, project_id)
    return APIResponse(data={"deleted": project_id})
