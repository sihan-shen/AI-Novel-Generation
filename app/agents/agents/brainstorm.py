"""Brainstorm Agent configuration."""

from pathlib import Path

from app.agents.base import AgentConfig, Tool
from app.agents.tools.brainstorm import list_pending_inspirations, save_inspiration
from app.agents.tools.shared import search_any
from app.agents.tools.writing import get_outline_context, lookup_settings


def _load_prompt() -> str:
    prompt_path = Path(__file__).parent.parent / "prompts" / "brainstorm_system.txt"
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    return "You are a creative writing consultant."


def build_brainstorm_config(
    db,
    project_id: str,
    task_id: str,
    max_steps: int = 50,
    token_budget: int = 100_000,
) -> AgentConfig:
    """Build a Brainstorm Agent configuration."""
    return AgentConfig(
        system_prompt=_load_prompt(),
        tools=[
            Tool(
                name="lookup_settings",
                description="Search project settings by keywords. Args: keywords (list[str])",
                parameters={"type": "object", "properties": {"keywords": {"type": "array", "items": {"type": "string"}}}},  # noqa: E501
                handler=lambda **kw: lookup_settings(db, keywords=kw["keywords"], project_id=project_id),  # noqa: E501
            ),
            Tool(
                name="get_outline_context",
                description="Get outline tree. Args: outline_id (str, optional)",
                parameters={"type": "object", "properties": {"outline_id": {"type": "string"}}},
                handler=lambda **kw: get_outline_context(db, project_id=project_id, outline_id=kw.get("outline_id")),  # noqa: E501
            ),
            Tool(
                name="search_any",
                description="Cross-entity search. Args: q (str), type (str, optional), limit (int, optional)",  # noqa: E501
                parameters={"type": "object", "properties": {"q": {"type": "string"}, "type": {"type": "string"}, "limit": {"type": "integer"}}},  # noqa: E501
                handler=lambda **kw: search_any(db, q=kw.get("q", ""), type=kw.get("type", "all"), limit=kw.get("limit", 20), project_id=project_id),  # noqa: E501
            ),
            Tool(
                name="save_inspiration",
                description="Propose saving a brainstorm result. Args: insp_type (str: idea|setting|outline), title (str), content (str), category (str, optional)",  # noqa: E501
                parameters={"type": "object", "properties": {"insp_type": {"type": "string"}, "title": {"type": "string"}, "content": {"type": "string"}, "category": {"type": "string"}}},  # noqa: E501
                handler=lambda **kw: save_inspiration(db, task_id=task_id, insp_type=kw["insp_type"], title=kw["title"], content=kw["content"], category=kw.get("category", "")),  # noqa: E501
            ),
            Tool(
                name="list_pending_inspirations",
                description="List pending inspirations from the current brainstorm session. Args: none",  # noqa: E501
                parameters={"type": "object", "properties": {}},
                handler=lambda **kw: list_pending_inspirations(db, task_id=task_id),
            ),
        ],
        temperature=0.9,
        max_steps=max_steps,
        token_budget=token_budget,
    )
