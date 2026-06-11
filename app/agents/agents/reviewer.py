"""Reviewer Agent configuration."""

from app.agents.base import AgentConfig, Tool
from app.agents.tools.review import (
    get_chapter_content, check_setting_consistency,
    check_style_consistency, check_logic_structure, submit_review,
)
from app.agents.tools.writing import get_style_guide, get_recent_chapters
from app.agents.tools.shared import search_any
from pathlib import Path


def _load_prompt() -> str:
    path = Path(__file__).parent.parent / "prompts" / "reviewer_system.txt"
    return path.read_text(encoding="utf-8") if path.exists() else "You are a reviewer."


def build_reviewer_config(
    db, project_id: str, chapter_id: str, blackboard,
    write_mode: str = "draft", task_id: str | None = None,
) -> AgentConfig:
    return AgentConfig(
        system_prompt=_load_prompt(),
        tools=[
            Tool(name="get_chapter_content", description="Get full chapter content. Args: none",
                 parameters={"type": "object", "properties": {}},
                 handler=lambda **kw: get_chapter_content(db, chapter_id=chapter_id)),
            Tool(name="get_style_guide", description="Get style guide. Args: none",
                 parameters={"type": "object", "properties": {}},
                 handler=lambda **kw: get_style_guide(db, project_id=project_id)),
            Tool(name="get_recent_chapters", description="Get recent chapters. Args: count (int, opt)",
                 parameters={"type": "object", "properties": {"count": {"type": "integer"}}},
                 handler=lambda **kw: get_recent_chapters(db, project_id=project_id, count=kw.get("count", 3))),
            Tool(name="check_setting_consistency", description="Check settings consistency. Args: none",
                 parameters={"type": "object", "properties": {}},
                 handler=lambda **kw: check_setting_consistency(db, chapter_id=chapter_id, project_id=project_id)),
            Tool(name="check_style_consistency", description="Check style consistency. Args: none",
                 parameters={"type": "object", "properties": {}},
                 handler=lambda **kw: check_style_consistency(db, chapter_id=chapter_id, project_id=project_id)),
            Tool(name="check_logic_structure", description="Check logic and structure. Args: none",
                 parameters={"type": "object", "properties": {}},
                 handler=lambda **kw: check_logic_structure(db, chapter_id=chapter_id, project_id=project_id)),
            Tool(name="submit_review", description="Submit review report with scores. Args: overall_score, setting_score, style_score, logic_score, findings (list), summary (str)",
                 parameters={"type": "object", "properties": {"overall_score": {"type": "number"}, "setting_score": {"type": "number"}, "style_score": {"type": "number"}, "logic_score": {"type": "number"}, "findings": {"type": "array"}, "summary": {"type": "string"}}},
                 handler=lambda **kw: submit_review(db, project_id=project_id, chapter_id=chapter_id, **kw, write_mode=write_mode, task_id=task_id),
                 confirm_before=True),
            Tool(name="search_any", description="Cross-entity search. Args: q (str)",
                 parameters={"type": "object", "properties": {"q": {"type": "string"}}},
                 handler=lambda **kw: search_any(db, q=kw.get("q", ""))),
        ],
        model="claude-sonnet-4-6", temperature=0.3,
    )
