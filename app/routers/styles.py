from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.response import APIResponse
from app.services.style_service import StyleService


class StyleResponse(BaseModel):
    id: str
    name: str
    source: str
    source_text: str
    analysis: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


router = APIRouter(prefix="/api/styles", tags=["styles"])


@router.get("", response_model=APIResponse[list[StyleResponse]])
async def list_styles(db: Session = Depends(get_db)):
    styles = StyleService.list_all(db)
    return APIResponse(data=styles)


@router.delete("/{style_id}", response_model=APIResponse[dict])
async def delete_style(style_id: str, db: Session = Depends(get_db)):
    StyleService.delete(db, style_id)
    return APIResponse(data={"deleted": style_id})
