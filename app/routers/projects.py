from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.project import ProjectCreate, ProjectResponse
from app.schemas.response import APIResponse
from app.services.project_service import ProjectService

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=APIResponse[list[ProjectResponse]])
async def list_projects(db: Session = Depends(get_db)):
    projects = ProjectService.list(db)
    return APIResponse(data=projects)


@router.post("", response_model=APIResponse[ProjectResponse], status_code=201)
async def create_project(body: ProjectCreate, db: Session = Depends(get_db)):
    project = ProjectService.create(db, body)
    return APIResponse(data=project)


@router.get("/{project_id}", response_model=APIResponse[ProjectResponse])
async def get_project(project_id: str, db: Session = Depends(get_db)):
    project = ProjectService.get(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return APIResponse(data=project)


@router.delete("/{project_id}", response_model=APIResponse[dict])
async def delete_project(project_id: str, db: Session = Depends(get_db)):
    ProjectService.delete(db, project_id)
    return APIResponse(data={"deleted": project_id})
