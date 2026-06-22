from pathlib import Path

import yaml
from sqlalchemy.orm import Session

from app.services.chapter_service import ChapterService
from app.services.setting_service import SettingService


class ContextBuilder:
    """Assembles structured context for LLM calls based on scenario type."""

    SCENARIOS = ["brainstorm", "review"]

    def __init__(self, db: Session):
        self.db = db
        self._templates: dict = {}

    def _load_template(self, scenario: str) -> dict:
        path = Path(__file__).parent / "templates" / f"{scenario}.yaml"
        if not path.exists():
            return {"system": "You are a novel writing assistant.", "template": "{{ request }}"}
        with open(path) as f:
            return yaml.safe_load(f) or {}

    def build(self, scenario: str, project_id: str, **kwargs) -> list[dict]:
        """Build messages list for LLM API call."""
        template = self._load_template(scenario)
        system = template.get("system", "")
        prompt_template = template.get("template", "")

        context_parts = []

        # Project info
        from app.services.project_service import ProjectService
        project = ProjectService.get(self.db, project_id)
        if project:
            context_parts.append(f"项目类型: {project.genre}\n项目状态: {project.status}")

        # Settings summary
        context_parts.append(SettingService.build_llm_context(self.db, project_id))

        # Recent chapters for context
        recent_chapters = ChapterService.list_by_project(self.db, project_id)
        if recent_chapters:
            last = recent_chapters[-1]
            context_parts.append(f"=== 最近章节 ===\n标题: {last.title}\n内容预览: {last.content[:300]}")  # noqa: E501

        # Build user prompt from template
        from jinja2 import Template
        user_prompt = Template(prompt_template).render(
            context="\n".join(context_parts),
            **kwargs
        )

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user_prompt})
        return messages
