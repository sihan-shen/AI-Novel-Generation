from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from pathlib import Path
from fastapi.templating import Jinja2Templates

from app.database import get_db
from app.schemas.setting import SettingCreate, SettingUpdate
from app.services.setting_service import SettingService, CATEGORIES
from app.services.project_service import ProjectService
from app.services.cleaning_service import CleaningService

router = APIRouter(prefix="/project/{project_id}/settings", tags=["settings"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("", response_class=HTMLResponse)
async def settings_page(project_id: str, request: Request, category: str | None = None, db: Session = Depends(get_db)):
    project = ProjectService.get(db, project_id)
    if not project:
        return HTMLResponse("Not found", 404)
    settings = SettingService.list_by_project(db, project_id, category)
    return templates.TemplateResponse(request, "settings/index.html", {
        "project": project, "settings": settings,
        "categories": CATEGORIES, "current_category": category or "全部",
    })


@router.get("/list")
async def settings_list(project_id: str, request: Request, category: str | None = None, db: Session = Depends(get_db)):
    settings = SettingService.list_by_project(db, project_id, category)
    return templates.TemplateResponse(request, "settings/_list.html", {"settings": settings, "project_id": project_id})


@router.get("/new")
async def new_setting_form(project_id: str, request: Request, category: str):
    return templates.TemplateResponse(request, "settings/_form.html", {
        "project_id": project_id, "category": category, "is_edit": False,
        "item": None, "post_url": f"/project/{project_id}/settings/create",
    })


@router.post("/create")
async def create_setting(request: Request, project_id: str, db: Session = Depends(get_db)):
    form = await request.form()
    data = SettingCreate(
        project_id=project_id, category=form["category"], name=form["name"],
        summary=form.get("summary", ""), content=form.get("content", ""),
        weight=int(form.get("weight", 5)),
    )
    SettingService.create(db, data)
    settings = SettingService.list_by_project(db, project_id)
    return templates.TemplateResponse(request, "settings/_list.html", {"settings": settings, "project_id": project_id})


@router.put("/{setting_id}")
async def update_setting(setting_id: str, request: Request, project_id: str, db: Session = Depends(get_db)):
    form = await request.form()
    from app.schemas.setting import SettingUpdate
    data = SettingUpdate(
        name=form.get("name"),
        category=form.get("category"),
        summary=form.get("summary"),
        content=form.get("content"),
        weight=int(form.get("weight", 5)) if form.get("weight") else None,
    )
    SettingService.update(db, setting_id, data)
    settings = SettingService.list_by_project(db, project_id)
    return templates.TemplateResponse(request, "settings/_list.html", {"settings": settings, "project_id": project_id})


@router.post("/clean")
async def clean_settings(project_id: str, request: Request, db: Session = Depends(get_db)):
    basic = CleaningService.basic_clean(db, project_id)
    deep = CleaningService.deep_clean(db, project_id)
    return templates.TemplateResponse(request, "settings/_clean_report.html", {
        "basic": basic, "deep": deep,
    })


@router.get("/{setting_id}")
async def setting_detail(setting_id: str, request: Request, db: Session = Depends(get_db)):
    setting = SettingService.get(db, setting_id)
    if not setting:
        return HTMLResponse("Not found", 404)
    relations = SettingService.get_relations(db, setting_id)
    return templates.TemplateResponse(request, "settings/_detail.html", {
        "setting": setting, "relations": relations,
    })


@router.post("/reorder")
async def reorder_settings(project_id: str, request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    SettingService.reorder(db, data["items"])
    return HTMLResponse("ok")


@router.delete("/{setting_id}")
async def delete_setting(project_id: str, setting_id: str, request: Request, db: Session = Depends(get_db)):
    SettingService.delete(db, setting_id)
    settings = SettingService.list_by_project(db, project_id)
    return templates.TemplateResponse(request, "settings/_list.html", {"settings": settings, "project_id": project_id})
