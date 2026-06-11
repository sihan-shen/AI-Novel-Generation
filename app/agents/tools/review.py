"""Reviewer Agent tool handlers."""

import json
from sqlalchemy.orm import Session
from app.services.chapter_service import ChapterService
from app.services.setting_service import SettingService
from app.services.review_service import ReviewService


def get_chapter_content(db: Session, chapter_id: str) -> str:
    """Get a chapter's full content."""
    ch = ChapterService.get(db, chapter_id)
    if not ch:
        return json.dumps({"error": "Chapter not found"})
    return json.dumps({
        "id": ch.id, "title": ch.title, "content": ch.content or "", "word_count": ch.word_count,
    }, ensure_ascii=False)


def check_setting_consistency(db: Session, chapter_id: str, project_id: str) -> str:
    """Check chapter content against active settings."""
    ch = ChapterService.get(db, chapter_id)
    if not ch:
        return json.dumps({"error": "Chapter not found"})
    settings = SettingService.list_by_project(db, project_id)
    active = [s for s in settings if s.status == "active"]
    return json.dumps({
        "total_settings_checked": len(active),
        "chapter_id": chapter_id,
        "preview_ready": True,
    }, ensure_ascii=False)


def check_style_consistency(db: Session, chapter_id: str, project_id: str) -> str:
    return json.dumps({"status": "ready", "message": "Style check context prepared"})


def check_logic_structure(db: Session, chapter_id: str, project_id: str) -> str:
    return json.dumps({"status": "ready", "message": "Logic check context prepared"})


def submit_review(
    db: Session, project_id: str, chapter_id: str,
    overall_score: float, setting_score: float, style_score: float,
    logic_score: float, findings: list, summary: str,
    write_mode: str = "draft", task_id: str | None = None,
) -> str:
    """Submit a review report."""
    review_data = {
        "overall_score": overall_score,
        "setting_consistency_score": setting_score,
        "style_consistency_score": style_score,
        "logic_structure_score": logic_score,
    }
    review = ReviewService.create_review(
        db, project_id=project_id, chapter_id=chapter_id,
        scope="agent", summary=review_data, findings=findings,
    )
    if task_id:
        review.triggered_by_type = "agent"
        review.triggered_by_task_id = task_id
        db.commit()
    return json.dumps({
        "review_id": review.id, "overall_score": overall_score, "status": "submitted",
    }, ensure_ascii=False)
