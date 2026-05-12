from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from pathlib import Path
from fastapi.templating import Jinja2Templates

from app.database import get_db
from app.services.review_service import ReviewService
from app.services.chapter_service import ChapterService
from app.services.project_service import ProjectService

router = APIRouter(prefix="/project/{project_id}/review", tags=["review"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("", response_class=HTMLResponse)
async def review_page(project_id: str, request: Request, db: Session = Depends(get_db)):
    project = ProjectService.get(db, project_id)
    if not project:
        return HTMLResponse("Not found", 404)
    reviews = ReviewService.list_reviews(db, project_id)
    return templates.TemplateResponse(request, "review/index.html", {"project": project, "reviews": reviews})


@router.get("/new")
async def new_review_form(project_id: str, request: Request, db: Session = Depends(get_db)):
    chapters = ChapterService.list_by_project(db, project_id)
    return templates.TemplateResponse(request, "review/_form.html", {"project_id": project_id, "chapters": chapters})


@router.post("/run")
async def run_review(project_id: str, request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    chapter_id = form.get("chapter_id") or None
    if not chapter_id:
        return HTMLResponse("请选择要审阅的章节", status_code=400)
    chapter = ChapterService.get(db, chapter_id)
    if not chapter:
        return HTMLResponse("章节未找到", status_code=404)
    result = await ReviewService.run_review(db, chapter)
    ReviewService.create_review(db, project_id, chapter_id, "batch", result["summary"], result["findings"])
    reviews = ReviewService.list_reviews(db, project_id)
    return templates.TemplateResponse(request, "review/_list.html", {"reviews": reviews, "project_id": project_id})


@router.get("/{review_id}")
async def review_detail(review_id: str, request: Request, db: Session = Depends(get_db)):
    review = ReviewService.get_review(db, review_id)
    if not review:
        return HTMLResponse("Not found", 404)
    return templates.TemplateResponse(request, "review/_detail.html", {"review": review})


@router.get("/list")
async def review_list(project_id: str, request: Request, db: Session = Depends(get_db)):
    reviews = ReviewService.list_reviews(db, project_id)
    return templates.TemplateResponse(request, "review/_list.html", {"reviews": reviews, "project_id": project_id})
