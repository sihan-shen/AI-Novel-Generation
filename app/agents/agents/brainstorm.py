"""Brainstorm Agent configuration."""

from pathlib import Path
from app.agents.base import AgentConfig, Tool
from app.agents.tools.writing import lookup_settings, get_outline_context
from app.agents.tools.shared import search_any
from app.agents.tools.brainstorm import save_inspiration


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
                parameters={"type": "object", "properties": {"keywords": {"type": "array", "items": {"type": "string"}}}},
                handler=lambda **kw: lookup_settings(db, keywords=kw["keywords"], project_id=project_id),
            ),
            Tool(
                name="get_outline_context",
                description="Get outline tree. Args: outline_id (str, optional)",
                parameters={"type": "object", "properties": {"outline_id": {"type": "string"}}},
                handler=lambda **kw: get_outline_context(db, project_id=project_id, outline_id=kw.get("outline_id")),
            ),
            Tool(
                name="search_any",
                description="Cross-entity search. Args: q (str), type (str, optional), limit (int, optional)",
                parameters={"type": "object", "properties": {"q": {"type": "string"}, "type": {"type": "string"}, "limit": {"type": "integer"}}},
                handler=lambda **kw: search_any(db, q=kw.get("q", ""), type=kw.get("type", "all"), limit=kw.get("limit", 20)),
            ),
            Tool(
                name="save_inspiration",
                description="Propose saving a brainstorm result. Args: insp_type (str: idea|setting|outline), title (str), content (str), category (str, optional)",
                parameters={"type": "object", "properties": {"insp_type": {"type": "string"}, "title": {"type": "string"}, "content": {"type": "string"}, "category": {"type": "string"}}},
                handler=lambda **kw: save_inspiration(db, task_id=task_id, insp_type=kw["insp_type"], title=kw["title"], content=kw["content"], category=kw.get("category", "")),
            ),
        ],
        model="claude-sonnet-4-6",
        temperature=0.9,
        max_steps=max_steps,
        token_budget=token_budget,
    )
