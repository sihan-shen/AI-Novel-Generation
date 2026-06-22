"""Shared tools available to all agents."""

from sqlalchemy.orm import Session

from app.services.search_service import SearchService


def search_any(db: Session, q: str = "", type: str = "all", limit: int = 20, project_id: str | None = None) -> str:  # noqa: E501
    """Cross-entity search. Returns JSON list of results."""
    import json
    results = SearchService.search(db, q=q, type=type, limit=limit, project_id=project_id)
    return json.dumps(results, ensure_ascii=False)


def report_progress(blackboard, message: str) -> str:
    """Write progress message to blackboard. Visible to user."""
    blackboard.emit_event({
        "type": "progress",
        "message": message,
    })
    return "ok"
