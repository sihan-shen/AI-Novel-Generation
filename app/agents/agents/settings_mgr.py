"""Setting Manager Agent configuration."""

from pathlib import Path

from app.agents.base import AgentConfig, Tool
from app.agents.tools.setting import (
    detect_conflicts,
    get_related_settings,
    get_setting_detail,
    link_settings,
    propose_setting,
    resolve_conflict,
    search_settings,
)
from app.agents.tools.shared import search_any


def _load_prompt() -> str:
    path = Path(__file__).parent.parent / "prompts" / "settings_mgr_system.txt"
    return path.read_text(encoding="utf-8") if path.exists() else "You are a setting manager."


def build_settings_mgr_config(
    db, project_id: str, blackboard,
    write_mode: str = "suggest", task_id: str | None = None,
) -> AgentConfig:
    return AgentConfig(
        system_prompt=_load_prompt(),
        tools=[
            Tool(name="search_settings", description="Search settings. Args: keywords (str), category (str, opt)",  # noqa: E501
                 parameters={"type": "object", "properties": {"keywords": {"type": "string"}, "category": {"type": "string"}}},  # noqa: E501
                 handler=lambda **kw: search_settings(db, project_id=project_id, **kw)),
            Tool(name="get_setting_detail", description="Get setting detail. Args: setting_id (str)",  # noqa: E501
                 parameters={"type": "object", "properties": {"setting_id": {"type": "string"}}},
                 handler=lambda **kw: get_setting_detail(db, setting_id=kw["setting_id"])),
            Tool(name="get_related_settings", description="Get related settings. Args: setting_id (str)",  # noqa: E501
                 parameters={"type": "object", "properties": {"setting_id": {"type": "string"}}},
                 handler=lambda **kw: get_related_settings(db, setting_id=kw["setting_id"])),
            Tool(name="propose_setting", description="Propose create/update setting. Args: category, name, key, summary, content, weight (int)",  # noqa: E501
                 parameters={"type": "object", "properties": {"category": {"type": "string"}, "name": {"type": "string"}, "key": {"type": "string"}, "summary": {"type": "string"}, "content": {"type": "string"}, "weight": {"type": "integer"}}},  # noqa: E501
                 handler=lambda **kw: propose_setting(db, project_id=project_id, **kw, write_mode=write_mode, task_id=task_id, blackboard=blackboard),  # noqa: E501
                 confirm_before=True),
            Tool(name="detect_conflicts", description="Detect setting conflicts. Args: new_setting_ids (list)",  # noqa: E501
                 parameters={"type": "object", "properties": {"new_setting_ids": {"type": "array", "items": {"type": "string"}}}},  # noqa: E501
                 handler=lambda **kw: detect_conflicts(db, project_id=project_id, **kw)),
            Tool(name="resolve_conflict", description="Resolve a conflict. Args: conflict_desc (str), resolution (str)",  # noqa: E501
                 parameters={"type": "object", "properties": {"conflict_desc": {"type": "string"}, "resolution": {"type": "string"}}},  # noqa: E501
                 handler=lambda **kw: resolve_conflict(db, **kw, write_mode=write_mode)),
            Tool(name="link_settings", description="Link two settings. Args: from_setting_id, to_setting_id, relation_type, description",  # noqa: E501
                 parameters={"type": "object", "properties": {"from_setting_id": {"type": "string"}, "to_setting_id": {"type": "string"}, "relation_type": {"type": "string"}, "description": {"type": "string"}}},  # noqa: E501
                 handler=lambda **kw: link_settings(db, **kw)),
            Tool(name="search_any", description="Cross-entity search. Args: q (str)",
                 parameters={"type": "object", "properties": {"q": {"type": "string"}}},
                 handler=lambda **kw: search_any(db, q=kw.get("q", ""), project_id=project_id)),
        ],
        temperature=0.3,
    )
