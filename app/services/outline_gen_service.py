import json
from typing import AsyncGenerator
from sqlalchemy.orm import Session
from app.llm.adapter import get_adapter
from app.llm.prompts.loader import load as load_prompt
from app.services.outline_service import OutlineService
from app.schemas.outline import OutlineCreate


class OutlineGenerationError(Exception):
    pass


class OutlineGenerationService:
    """AI-powered outline generation, step by step."""

    @staticmethod
    async def generate_volumes_stream(
        db: Session, project_id: str, story_desc: str, setting_ids: list[str] | None = None
    ) -> AsyncGenerator[str, None]:
        """Generate volume structure from story description."""
        prompt = load_prompt("outline_gen_volume")
        context = OutlineGenerationService._build_context(db, project_id, setting_ids)

        system_content = prompt
        if context:
            system_content += f"\n\n## 项目设定参考\n{context}"

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": f"请根据以下故事描述，设计整部小说的卷结构：\n\n{story_desc}"},
        ]

        adapter = get_adapter(db)
        async for chunk in adapter.generate_stream(messages, temperature=0.7, max_tokens=4096):
            yield chunk

    @staticmethod
    async def generate_chapters_stream(
        db: Session, project_id: str, volume_title: str, volume_summary: str, count: int = 0
    ) -> AsyncGenerator[str, None]:
        """Generate chapters under a volume."""
        prompt = load_prompt("outline_gen_chapter")
        context = OutlineGenerationService._build_context(db, project_id)

        system_content = prompt
        if context:
            system_content += f"\n\n## 项目设定参考\n{context}"

        user_msg = f"卷标题：{volume_title}\n卷概要：{volume_summary}\n"
        if count > 0:
            user_msg += f"请生成 {count} 章。"
        else:
            user_msg += "请根据卷的内容自动决定章节数量。"

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_msg},
        ]

        adapter = get_adapter(db)
        async for chunk in adapter.generate_stream(messages, temperature=0.7, max_tokens=4096):
            yield chunk

    @staticmethod
    async def generate_sections_stream(
        db: Session, project_id: str, chapter_title: str, chapter_summary: str, count: int = 0
    ) -> AsyncGenerator[str, None]:
        """Generate sections under a chapter."""
        prompt = load_prompt("outline_gen_section")
        context = OutlineGenerationService._build_context(db, project_id)

        system_content = prompt
        if context:
            system_content += f"\n\n## 项目设定参考\n{context}"

        user_msg = f"章标题：{chapter_title}\n章概要：{chapter_summary}\n"
        if count > 0:
            user_msg += f"请生成 {count} 个细节点。"
        else:
            user_msg += "请根据章的内容自动决定细节点数量。"

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_msg},
        ]

        adapter = get_adapter(db)
        async for chunk in adapter.generate_stream(messages, temperature=0.7, max_tokens=4096):
            yield chunk

    @staticmethod
    async def generate_content_stream(
        db: Session, project_id: str, chapter_title: str, sections: list[dict]
    ) -> AsyncGenerator[str, None]:
        """Generate chapter content from sections."""
        prompt = load_prompt("outline_gen_content")
        context = OutlineGenerationService._build_context(db, project_id)

        system_content = prompt
        if context:
            system_content += f"\n\n## 项目设定参考\n{context}"

        sections_text = "\n".join(
            f"- {s.get('title', '')}: {s.get('summary', '')}（{s.get('notes', '')}）"
            for s in sections
        )

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": f"章标题：{chapter_title}\n\n细纲：\n{sections_text}\n\n请根据以上细纲撰写正文。"},
        ]

        adapter = get_adapter(db)
        async for chunk in adapter.generate_stream(messages, temperature=0.8, max_tokens=8192):
            yield chunk

    @staticmethod
    def confirm_save(db: Session, project_id: str, items: list[dict], parent_id: str | None = None) -> int:
        """Batch save generated outlines to DB. Returns count saved."""
        count = 0
        for item in items:
            data = OutlineCreate(
                project_id=project_id,
                parent_id=parent_id,
                level=item.get("level", 1),
                title=item.get("title", ""),
                summary=item.get("summary", ""),
                notes=item.get("notes", ""),
            )
            children = item.pop("children", None)
            obj = OutlineService.create(db, data)
            count += 1
            if children:
                count += OutlineGenerationService.confirm_save(db, project_id, children, obj.id)
        return count

    @staticmethod
    def _build_context(db: Session, project_id: str, setting_ids: list[str] | None = None) -> str:
        """Build project context string for prompts."""
        from app.services.setting_service import SettingService
        return SettingService.build_llm_context(db, project_id, setting_ids)
