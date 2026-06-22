"""Reviewer Agent tool handlers."""

import asyncio
import contextlib
import json
from collections.abc import Callable
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


# ---------------------------------------------------------------------------
# Core consistency check — extracted from the 3 near-identical functions below
# ---------------------------------------------------------------------------

def _run_consistency_check(
    db: Session,
    chapter_id: str,
    project_id: str,
    *,
    dimension: str,
    context_builder: Callable[[Session, str, str], str],
    scenario: str,
    reviewer_role: str,
    check_items: str,
    context_label: str,
) -> dict:
    """Run a single-dimension consistency check against chapter content.

    Parameters
    ----------
    context_builder : (db, chapter_id, project_id) -> context_text
        Callable that fetches the relevant reference material (e.g. active
        settings, style guide, recent chapters) and returns it as a string.
    """
    # 1. Fetch chapter
    try:
        ch = ChapterService.get(db, chapter_id)
    except Exception as e:
        return {"error": f"Failed to retrieve chapter: {e}"}
    if not ch:
        return {"error": "Chapter not found"}

    # 2. Build review context (settings / style guide / recent chapters)
    try:
        context_text = context_builder(db, chapter_id, project_id)
    except Exception as e:
        return {"error": f"Failed to build review context: {e}"}

    # 3. Build prompt
    prompt = (
        f"You are a {reviewer_role}. Given a chapter and {context_label.lower()}, "
        f"check for {check_items}.\n\n"
        "Return ONLY valid JSON in this exact format:\n"
        '{"score": float (0-5), "findings": [string], "summary": string}\n\n'
        f"Chapter: {ch.title}\n"
        f"Content: {ch.content or ''}\n\n"
        f"{context_label}:\n{context_text}"
    )

    # 4. Get adapter
    try:
        adapter = get_adapter(db)
    except Exception as e:
        return {"error": f"Failed to get LLM adapter: {e}"}

    # 5. Call LLM
    try:
        response = _sync_generate(
            adapter,
            [{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=1024,
        )
    except TimeoutError:
        return {
            "dimension": dimension,
            "score": 0,
            "findings": [],
            "summary": "LLM request timed out",
        }
    except Exception as e:
        return {
            "dimension": dimension,
            "score": 0,
            "findings": [],
            "summary": f"LLM request failed: {e}",
        }

    # 6. Record usage (best-effort)
    with contextlib.suppress(Exception):
        record_usage(
            db, adapter.model, response.usage,  # type: ignore[attr-defined]
            scenario=scenario, project_id=project_id,
        )

    # 7. Parse and return
    return _parse_review_response(response.content, dimension)


# ---------------------------------------------------------------------------
# Public tool handlers (thin wrappers around _run_consistency_check)
# ---------------------------------------------------------------------------

def check_setting_consistency(db: Session, chapter_id: str, project_id: str) -> dict:
    """Check chapter content against active settings using LLM."""

    def _build_context(d: Session, _cid: str, pid: str) -> str:
        try:
            settings = SettingService.list_by_project(d, pid)
        except Exception as e:
            return f"（获取设定失败: {e}）"
        active = [s for s in settings if s.status == "active"]
        return "\n".join(
            f"- {s.name} ({s.key}): {s.summary or ''} / {s.content or ''}"
            for s in active
        ) if active else "（无活跃设定）"

    return _run_consistency_check(
        db, chapter_id, project_id,
        dimension="setting",
        context_builder=_build_context,
        scenario="check_setting_consistency",
        reviewer_role="setting consistency reviewer",
        check_items="contradictions, violations, or inconsistencies",
        context_label="Active Settings",
    )


def check_style_consistency(db: Session, chapter_id: str, project_id: str) -> dict:
    """Check chapter content against the project's style guide using LLM."""

    def _build_context(d: Session, _cid: str, pid: str) -> str:
        from app.agents.tools.writing import get_style_guide
        return get_style_guide(d, pid)

    return _run_consistency_check(
        db, chapter_id, project_id,
        dimension="style",
        context_builder=_build_context,
        scenario="check_style_consistency",
        reviewer_role="style consistency reviewer",
        check_items="style deviations, tone mismatches, or writing inconsistencies",
        context_label="Style Guide",
    )


def check_logic_structure(db: Session, chapter_id: str, project_id: str) -> dict:
    """Check chapter content for plot logic and structural issues using LLM."""

    def _build_context(d: Session, _cid: str, pid: str) -> str:
        from app.agents.tools.writing import get_recent_chapters
        return get_recent_chapters(d, pid, count=3)

    return _run_consistency_check(
        db, chapter_id, project_id,
        dimension="logic",
        context_builder=_build_context,
        scenario="check_logic_consistency",
        reviewer_role="plot logic reviewer",
        check_items="plot holes, continuity issues, pacing problems, and structural flaws",
        context_label="Recent Chapters",
    )


# ---------------------------------------------------------------------------
# Utility tool
# ---------------------------------------------------------------------------

def get_chapter_content(db: Session, chapter_id: str) -> str:
    """Get a chapter's full content."""
    try:
        ch = ChapterService.get(db, chapter_id)
    except Exception as e:
        return json.dumps({"error": f"Failed to retrieve chapter: {e}"})
    if not ch:
        return json.dumps({"error": "Chapter not found"})
    return json.dumps({
        "id": ch.id, "title": ch.title, "content": ch.content or "",
        "word_count": ch.word_count,
    }, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Submission
# ---------------------------------------------------------------------------

def submit_review(
    db: Session, project_id: str, chapter_id: str,
    overall_score: float, setting_score: float, style_score: float,
    logic_score: float, findings: list, summary: str,
    write_mode: str = "draft", task_id: str | None = None,
) -> str:
    """Submit a review report.

    Parameters
    ----------
    summary : str
        Human-readable summary text — now wired into the persisted review_data.
    write_mode : str
        ``"suggest"`` returns the payload without persisting to the database;
        anything else (default ``"draft"`` / ``"write"``) persists a Review row.
    """
    review_data = {
        "overall_score": overall_score,
        "setting_consistency_score": setting_score,
        "style_consistency_score": style_score,
        "logic_structure_score": logic_score,
        "summary": summary,
    }

    # Suggest mode — return payload without DB persistence
    if write_mode == "suggest":
        return json.dumps({
            "overall_score": overall_score,
            "summary": summary,
            "status": "suggested",
        }, ensure_ascii=False)

    # Write mode — persist to DB
    try:
        review = ReviewService.create_review(
            db, project_id=project_id, chapter_id=chapter_id,
            scope="agent", summary=review_data, findings=findings,
        )
    except Exception as e:
        return json.dumps({"error": f"Failed to create review: {e}"})

    if task_id:
        review.triggered_by_type = "agent"  # type: ignore[assignment]
        review.triggered_by_task_id = task_id  # type: ignore[assignment]
        try:
            db.commit()
        except Exception as e:
            return json.dumps({"error": f"Failed to save review metadata: {e}"})

    return json.dumps({
        "review_id": review.id,
        "overall_score": overall_score,
        "status": "submitted",
    }, ensure_ascii=False)
