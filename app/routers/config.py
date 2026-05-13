from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from pathlib import Path
from fastapi.templating import Jinja2Templates

from app.database import get_db
from app.services.config_service import ConfigService
from app.llm.provider_registry import PROVIDERS, fetch_models

router = APIRouter(prefix="/config", tags=["config"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("", response_class=HTMLResponse)
async def config_page(request: Request, db: Session = Depends(get_db)):
    cfg = ConfigService.get_all(db)
    return templates.TemplateResponse(request, "config/index.html", {
        "cfg": cfg, "providers": PROVIDERS,
    })


@router.post("/save", response_class=HTMLResponse)
async def config_save(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    items = {}
    for key in ("llm_provider", "api_key", "base_url", "model"):
        if key in form:
            items[key] = form[key]
    ConfigService.set_many(db, items)
    cfg = ConfigService.get_all(db)
    return templates.TemplateResponse(request, "config/_form.html", {
        "cfg": cfg, "providers": PROVIDERS, "saved": True,
    })


@router.get("/fetch-models")
async def fetch_models_endpoint(request: Request, db: Session = Depends(get_db)):
    cfg = ConfigService.get_all(db)
    provider = cfg["llm_provider"]
    api_key = cfg["api_key"]
    base_url = cfg["base_url"]
    try:
        models = await fetch_models(provider, api_key, base_url)
        return templates.TemplateResponse(request, "config/_model_list.html", {
            "models": models, "current": cfg["model"],
        })
    except Exception as e:
        return HTMLResponse(
            f'<p class="text-sm text-red-500 mt-2">获取失败: {e}</p>'
        )
