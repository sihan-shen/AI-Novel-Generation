import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.outline import OutlineCreate, OutlineResponse, OutlineUpdate
from app.schemas.response import APIResponse
from app.services.outline_service import OutlineService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects/{project_id}/outlines", tags=["outlines"])


@router.get("", response_model=APIResponse[list[OutlineResponse]])
async def get_outline_tree(project_id: str, db: Session = Depends(get_db)):
    outlines = OutlineService.get_tree(db, project_id)
    return APIResponse(data=outlines)


@router.post("", response_model=APIResponse[OutlineResponse], status_code=201)
async def create_outline(project_id: str, body: OutlineCreate, db: Session = Depends(get_db)):
    data = body.model_copy(update={"project_id": project_id})
    outline = OutlineService.create(db, data)
    return APIResponse(data=outline)


@router.get("/{outline_id}", response_model=APIResponse[OutlineResponse])
async def get_outline(project_id: str, outline_id: str, db: Session = Depends(get_db)):
    outline = OutlineService.get(db, outline_id)
    if not outline:
        raise HTTPException(status_code=404, detail="Outline not found")
    return APIResponse(data=outline)


@router.put("/{outline_id}", response_model=APIResponse[OutlineResponse])
async def update_outline(project_id: str, outline_id: str, body: OutlineUpdate, db: Session = Depends(get_db)):  # noqa: E501
    outline = OutlineService.update(db, outline_id, body)
    if not outline:
        raise HTTPException(status_code=404, detail="Outline not found")
    return APIResponse(data=outline)


@router.delete("/{outline_id}", response_model=APIResponse[dict])
async def delete_outline(project_id: str, outline_id: str, db: Session = Depends(get_db)):
    ok, _ = OutlineService.delete(db, outline_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Outline not found")
    return APIResponse(data={"deleted": outline_id})


@router.post("/reorder", response_model=APIResponse[dict])
async def reorder_outlines(project_id: str, body: dict, db: Session = Depends(get_db)):
    OutlineService.reorder(db, body["items"])
    return APIResponse(data={"ok": True})

logger.info("Module %s loaded", __name__)
