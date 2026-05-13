from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from pathlib import Path
from fastapi.templating import Jinja2Templates

from app.database import get_db
from app.services.config_service import ConfigService

router = APIRouter(prefix="/config", tags=["config"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("", response_class=HTMLResponse)
async def config_page(request: Request, db: Session = Depends(get_db)):
    cfg = ConfigService.get_all(db)
    return templates.TemplateResponse(request, "config/index.html", {"cfg": cfg})


@router.post("/save", response_class=HTMLResponse)
async def config_save(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    items = {}
    for key in ("llm_provider", "claude_api_key", "openai_api_key", "claude_model", "openai_model"):
        if key in form:
            items[key] = form[key]
    ConfigService.set_many(db, items)
    cfg = ConfigService.get_all(db)
    return templates.TemplateResponse(request, "config/_form.html", {"cfg": cfg, "saved": True})
