from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.response import APIResponse
from app.services.config_service import ConfigService

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("", response_model=APIResponse[dict])
async def get_config(db: Session = Depends(get_db)):
    cfg = ConfigService.get_all(db)
    return APIResponse(data=cfg)


@router.post("", response_model=APIResponse[dict])
async def save_config(body: dict, db: Session = Depends(get_db)):
    for key in ("llm_provider", "api_key", "base_url", "model", "host", "port"):
        if key in body:
            ConfigService.set(db, key, body[key])
    cfg = ConfigService.get_all(db)
    return APIResponse(data=cfg)
