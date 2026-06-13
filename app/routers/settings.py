from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.setting import SettingCreate, SettingUpdate
from app.schemas.response import APIResponse
from app.services.setting_service import SettingService


class SettingResponse(BaseModel):
    id: str
    project_id: str
    category: str
    name: str
    summary: str
    content: str
    weight: int
    status: str
    tags: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


router = APIRouter(prefix="/api/projects/{project_id}/settings", tags=["settings"])


@router.get("", response_model=APIResponse[list[SettingResponse]])
async def list_settings(project_id: str, category: str | None = None, db: Session = Depends(get_db)):
    settings = SettingService.list_by_project(db, project_id, category)
    return APIResponse(data=settings)


@router.post("", response_model=APIResponse[SettingResponse], status_code=201)
async def create_setting(project_id: str, body: SettingCreate, db: Session = Depends(get_db)):
    data = body.model_copy(update={"project_id": project_id})
    setting = SettingService.create(db, data)
    return APIResponse(data=setting)


@router.get("/{setting_id}", response_model=APIResponse[dict])
async def get_setting(setting_id: str, project_id: str, db: Session = Depends(get_db)):
    setting = SettingService.get(db, setting_id)
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    relations = SettingService.get_relations(db, setting_id)
    return APIResponse(data={"setting": SettingResponse.model_validate(setting), "relations": relations})


@router.put("/{setting_id}", response_model=APIResponse[SettingResponse])
async def update_setting(setting_id: str, project_id: str, body: SettingUpdate, db: Session = Depends(get_db)):
    setting = SettingService.update(db, setting_id, body)
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    return APIResponse(data=setting)


@router.delete("/{setting_id}", response_model=APIResponse[dict])
async def delete_setting(setting_id: str, project_id: str, db: Session = Depends(get_db)):
    SettingService.delete(db, setting_id)
    return APIResponse(data={"deleted": setting_id})


@router.post("/reorder", response_model=APIResponse[dict])
async def reorder_settings(project_id: str, body: dict, db: Session = Depends(get_db)):
    SettingService.reorder(db, body["items"])
    return APIResponse(data={"ok": True})
