from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from pathlib import Path
from fastapi.templating import Jinja2Templates

from app.database import get_db
from app.services.brainstorm_service import BrainstormService

router = APIRouter(prefix="/brainstorm", tags=["brainstorm"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("")
async def brainstorm_page(request: Request):
    return templates.TemplateResponse(request, "brainstorm/index.html", {})


@router.post("/generate")
async def brainstorm_generate(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    mode = form.get("mode", "free")
    query = form.get("query", "")
    project_id = form.get("project_id") or None
    result = await BrainstormService.brainstorm(db, project_id, mode, query)
    return templates.TemplateResponse(request, "brainstorm/_result.html", {"result": result})
