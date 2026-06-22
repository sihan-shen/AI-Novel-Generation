"""Reviewer Agent tool handlers."""

import asyncio
import contextlib
import json
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy.orm import Session

from app.llm.adapter import get_adapter, record_usage
from app.services.chapter_service import ChapterService
from app.services.review_service import ReviewService
from app.services.setting_service import SettingService

# Thread pool for running async LLM calls from synchronous tool handlers.
_llm_pool = ThreadPoolExecutor(max_workers=2)


def _sync_generate(adapter, messages, **kwargs):
    """Run an async adapter.generate() from synchronous code."""
    async def _gen():
        return await adapter.generate(messages, **kwargs)

    try:
        asyncio.get_running_loop()
        return _llm_pool.submit(asyncio.run, _gen()).result(timeout=30)
    except RuntimeError:
        return asyncio.run(_gen())


def _parse_review_response(raw_content: str, dimension: str) -> dict:
    """Parse LLM JSON response into a structured review dict."""
    try:
        data = json.loads(raw_content)
        return {
            "dimension": dimension,
            "score": float(data.get("score", 0)),
            "findings": list(data.get("findings", [])),
            "summary": str(data.get("summary", "")),
        }
    except Exception:
        return {
            "dimension": dimension,
            "score": 0,
            "findings": [],
            "summary": "LLM parse error",
        }


def get_chapter_content(db: Session, chapter_id: str) -> str:
    """Get a chapter's full content."""
    ch = ChapterService.get(db, chapter_id)
    if not ch:
        return json.dumps({"error": "Chapter not found"})
    return json.dumps({
        "id": ch.id, "title": ch.title, "content": ch.content or "", "word_count": ch.word_count,
    }, ensure_ascii=False)


def check_setting_consistency(db: Session, chapter_id: str, project_id: str) -> dict:
    """Check chapter content against active settings using LLM."""
    ch = ChapterService.get(db, chapter_id)
    if not ch:
        return {"error": "Chapter not found"}

    settings = SettingService.list_by_project(db, project_id)
    active = [s for s in settings if s.status == "active"]
    settings_text = "\n".join(
        f"- {s.name} ({s.key}): {s.summary or ''} / {s.content or ''}" for s in active
    ) if active else "（无活跃设定）"

    prompt = (
        "You are a setting consistency reviewer. Given a chapter and active settings, "
        "check for contradictions, violations, or inconsistencies.\n\n"
        "Return ONLY valid JSON in this exact format:\n"
        '{"score": float (0-5), "findings": [string], "summary": string}\n\n'
        f"Chapter: {ch.title}\n"
        f"Content: {ch.content or ''}\n\n"
        f"Active Settings:\n{settings_text}"
    )

    adapter = get_adapter(db)
    response = _sync_generate(
        adapter,
        [{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=1024,
    )

    with contextlib.suppress(Exception):
            record_usage(
            db, adapter.model, response.usage,  # type: ignore[attr-defined]
            scenario="check_setting_consistency", project_id=project_id,
        )

    return _parse_review_response(response.content, "setting")


def check_style_consistency(db: Session, chapter_id: str, project_id: str) -> dict:
    """Check chapter content against the project's style guide using LLM."""
    ch = ChapterService.get(db, chapter_id)
    if not ch:
        return {"error": "Chapter not found"}

    from app.agents.tools.writing import get_style_guide
    style_guide = get_style_guide(db, project_id)

    prompt = (
        "You are a style consistency reviewer. Given a chapter and the project's style guide, "
        "check for style deviations, tone mismatches, or writing inconsistencies.\n\n"
        "Return ONLY valid JSON in this exact format:\n"
        '{"score": float (0-5), "findings": [string], "summary": string}\n\n'
        f"Chapter: {ch.title}\n"
        f"Content: {ch.content or ''}\n\n"
        f"Style Guide:\n{style_guide}"
    )

    adapter = get_adapter(db)
    response = _sync_generate(
        adapter,
        [{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=1024,
    )

    with contextlib.suppress(Exception):
            record_usage(
            db, adapter.model, response.usage,  # type: ignore[attr-defined]
            scenario="check_style_consistency", project_id=project_id,
        )

    return _parse_review_response(response.content, "style")


def check_logic_structure(db: Session, chapter_id: str, project_id: str) -> dict:
    """Check chapter content for plot logic and structural issues using LLM."""
    ch = ChapterService.get(db, chapter_id)
    if not ch:
        return {"error": "Chapter not found"}

    from app.agents.tools.writing import get_recent_chapters
    recent = get_recent_chapters(db, project_id, count=3)

    prompt = (
        "You are a plot logic reviewer. Given a chapter and recent chapters, "
        "check for plot holes, continuity issues, pacing problems, and structural flaws.\n\n"
        "Return ONLY valid JSON in this exact format:\n"
        '{"score": float (0-5), "findings": [string], "summary": string}\n\n'
        f"Chapter: {ch.title}\n"
        f"Content: {ch.content or ''}\n\n"
        f"Recent Chapters:\n{recent}"
    )

    adapter = get_adapter(db)
    response = _sync_generate(
        adapter,
        [{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=1024,
    )

    with contextlib.suppress(Exception):
            record_usage(
            db, adapter.model, response.usage,  # type: ignore[attr-defined]
            scenario="check_logic_consistency", project_id=project_id,
        )

    return _parse_review_response(response.content, "logic")


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
        review.triggered_by_type = "agent"  # type: ignore[assignment]
        review.triggered_by_task_id = task_id  # type: ignore[assignment]
        db.commit()
    return json.dumps({
        "review_id": review.id, "overall_score": overall_score, "status": "submitted",
    }, ensure_ascii=False)
