import json
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from pathlib import Path
from fastapi.templating import Jinja2Templates

from app.database import get_db
from app.services.brainstorm_service import BrainstormService
from app.services.idea_service import IdeaService
from app.services.project_service import ProjectService
from app.models.idea import Idea

router = APIRouter(prefix="/brainstorm", tags=["brainstorm"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("", response_class=HTMLResponse)
async def brainstorm_page(request: Request, db: Session = Depends(get_db)):
    projects = ProjectService.list(db)
    return templates.TemplateResponse(request, "brainstorm/index.html", {
        "projects": projects,
    })


@router.post("/chat")
async def brainstorm_chat(request: Request, db: Session = Depends(get_db)):
    body = await request.json()
    messages = body.get("messages", [])
    project_id = body.get("project_id")
    reply = await BrainstormService.chat(db, messages, project_id)
    return templates.TemplateResponse(request, "brainstorm/_message.html", {
        "msg": {"role": "assistant", "content": reply},
    })


@router.post("/extract")
async def brainstorm_extract(request: Request, db: Session = Depends(get_db)):
    body = await request.json()
    messages = body.get("messages", [])
    project_id = body.get("project_id")
    if not project_id:
        return HTMLResponse('<p class="text-sm text-red-500">请先选择目标项目</p>')
    result = await BrainstormService.extract(db, messages)
    return templates.TemplateResponse(request, "brainstorm/_extract.html", {
        "result": result,
        "project_id": project_id,
    })


@router.post("/confirm-save")
async def brainstorm_confirm_save(request: Request, db: Session = Depends(get_db)):
    body = await request.json()
    project_id = body.get("project_id")
    data = body.get("data", {})
    raw_messages = body.get("messages", [])
    saved = BrainstormService.confirm_save(db, project_id, data, raw_messages)
    return templates.TemplateResponse(request, "brainstorm/_saved.html", {
        "saved": saved,
        "project_id": project_id,
    })


@router.get("/history")
async def brainstorm_history(request: Request, db: Session = Depends(get_db)):
    ideas = IdeaService.list_by_project(db)
    brainstorm_ideas = [i for i in ideas if i.source == "brainstorm"]
    return templates.TemplateResponse(request, "brainstorm/_sidebar.html", {
        "saved_sessions": brainstorm_ideas,
    })


@router.get("/history/{idea_id}")
async def brainstorm_load(idea_id: str, request: Request, db: Session = Depends(get_db)):
    idea = db.query(Idea).filter(Idea.id == idea_id).first()
    if not idea:
        return HTMLResponse("Not found", 404)
    try:
        messages = json.loads(idea.content)
    except (json.JSONDecodeError, ValueError):
        messages = []
    return templates.TemplateResponse(request, "brainstorm/_chat.html", {
        "messages": messages,
        "loaded": True,
    })


@router.delete("/history/{idea_id}")
async def brainstorm_delete(idea_id: str, db: Session = Depends(get_db)):
    IdeaService.delete(db, idea_id)
    return HTMLResponse("ok")
