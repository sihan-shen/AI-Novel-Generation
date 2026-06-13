from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from pathlib import Path
from fastapi.templating import Jinja2Templates

from app.database import get_db
from app.services.style_service import StyleService

router = APIRouter(prefix="/styles", tags=["styles"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("", response_class=HTMLResponse)
async def styles_page(request: Request, db: Session = Depends(get_db)):
    styles = StyleService.list_all(db)
    return templates.TemplateResponse(request, "styles/index.html", {"styles": styles})


@router.get("/list")
async def styles_list(request: Request, db: Session = Depends(get_db)):
    styles = StyleService.list_all(db)
    return templates.TemplateResponse(request, "styles/_list.html", {"styles": styles})


@router.get("/import")
async def import_form(request: Request):
    return templates.TemplateResponse(request, "styles/_import.html", {})


@router.post("/analyze-slices")
async def analyze_slices(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    text = form.get("text", "")
    name = form.get("name", "未命名文风")
    slices = await StyleService.smart_slice(db, text)
    return templates.TemplateResponse(request, "styles/_slices.html", {
        "slices": slices, "full_text": text, "name": name,
    })


@router.post("/confirm-import")
async def confirm_import(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    name = form.get("name", "未命名文风")
    source_text = form.get("source_text", "")
    selected = form.get("selected_text", source_text[:500])
    analysis = await StyleService.analyze_text(db, selected)
    StyleService.create(db, name=name, source="智能导入", source_text=source_text, analysis=analysis)
    styles = StyleService.list_all(db)
    return templates.TemplateResponse(request, "styles/_list.html", {"styles": styles})


@router.delete("/{style_id}")
async def delete_style(style_id: str, db: Session = Depends(get_db)):
    StyleService.delete(db, style_id)
    return HTMLResponse("ok")


# ---- JSON API endpoints ----

from app.schemas.response import APIResponse
from pydantic import BaseModel
from datetime import datetime


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


api_router = APIRouter(prefix="/api/styles", tags=["styles"])


@api_router.get("", response_model=APIResponse[list[StyleResponse]])
async def api_list_styles(db: Session = Depends(get_db)):
    styles = StyleService.list_all(db)
    return APIResponse(data=styles)


@api_router.delete("/{style_id}", response_model=APIResponse[dict])
async def api_delete_style(style_id: str, db: Session = Depends(get_db)):
    StyleService.delete(db, style_id)
    return APIResponse(data={"deleted": style_id})
