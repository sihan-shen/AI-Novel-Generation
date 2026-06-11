"""Writer Agent configuration."""

from app.agents.base import AgentConfig, Tool
from app.agents.tools.writing import (
    lookup_settings, get_outline_context, get_recent_chapters,
    get_style_guide, write_chapter, update_outline_status,
)
from app.agents.tools.shared import search_any
from pathlib import Path


def _load_prompt() -> str:
    prompt_path = Path(__file__).parent.parent / "prompts" / "writer_system.txt"
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    return "You are a professional fiction writer."


def build_writer_config(
    db, project_id: str, blackboard,
    write_mode: str = "draft", task_id: str | None = None,
) -> AgentConfig:
    """Build a Writer Agent configuration."""
    return AgentConfig(
        system_prompt=_load_prompt(),
        tools=[
            Tool(
                name="lookup_settings",
                description="Search settings by keywords. Args: keywords (list[str])",
                parameters={"type": "object", "properties": {"keywords": {"type": "array", "items": {"type": "string"}}}},
                handler=lambda **kw: lookup_settings(db, keywords=kw["keywords"], project_id=project_id),
            ),
            Tool(
                name="get_outline_context",
                description="Get outline tree for the project. Args: outline_id (str, optional)",
                parameters={"type": "object", "properties": {"outline_id": {"type": "string"}}},
                handler=lambda **kw: get_outline_context(db, project_id=project_id, outline_id=kw.get("outline_id")),
            ),
            Tool(
                name="get_recent_chapters",
                description="Get recent N chapters. Args: count (int, optional, default 3)",
                parameters={"type": "object", "properties": {"count": {"type": "integer"}}},
                handler=lambda **kw: get_recent_chapters(db, project_id=project_id, count=kw.get("count", 3)),
            ),
            Tool(
                name="get_style_guide",
                description="Get the project's style guide configuration",
                parameters={"type": "object", "properties": {}},
                handler=lambda **kw: get_style_guide(db, project_id=project_id),
            ),
            Tool(
                name="write_chapter",
                description="Write/update a chapter. Args: outline_id (str), title (str), content (str), sort_order (int, optional)",
                parameters={"type": "object", "properties": {"outline_id": {"type": "string"}, "title": {"type": "string"}, "content": {"type": "string"}, "sort_order": {"type": "integer"}}},
                handler=lambda **kw: write_chapter(
                    db, project_id=project_id, outline_id=kw["outline_id"],
                    title=kw["title"], content=kw["content"],
                    sort_order=kw.get("sort_order", 1),
                    write_mode=write_mode, task_id=task_id, blackboard=blackboard,
                ),
            ),
            Tool(
                name="update_outline_status",
                description="Update outline node status. Args: outline_id (str), status (str, optional, default 'done')",
                parameters={"type": "object", "properties": {"outline_id": {"type": "string"}, "status": {"type": "string"}}},
                handler=lambda **kw: update_outline_status(db, outline_id=kw["outline_id"], status=kw.get("status", "done"), write_mode=write_mode),
            ),
            Tool(
                name="search_any",
                description="Cross-entity search. Args: q (str), type (str, optional), limit (int, optional)",
                parameters={"type": "object", "properties": {"q": {"type": "string"}, "type": {"type": "string"}, "limit": {"type": "integer"}}},
                handler=lambda **kw: search_any(db, q=kw.get("q", ""), type=kw.get("type", "all"), limit=kw.get("limit", 20)),
            ),
            Tool(
                name="report_progress",
                description="Report progress. Args: message (str)",
                parameters={"type": "object", "properties": {"message": {"type": "string"}}},
                handler=lambda **kw: (blackboard.emit_event({"type": "progress", "message": kw["message"]}), "ok")[1] if blackboard else "ok",
            ),
        ],
        model="claude-sonnet-4-6",
        temperature=0.7,
        token_budget=blackboard.autonomy_config.token_budget if blackboard else 100_000,
    )
