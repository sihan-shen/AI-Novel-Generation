import json
from sqlalchemy.orm import Session
from app.llm.context_builder import ContextBuilder
from app.llm.adapter import get_adapter, record_usage
from app.services.setting_service import SettingService
from app.services.outline_service import OutlineService
from app.services.idea_service import IdeaService
from app.schemas.setting import SettingCreate
from app.schemas.outline import OutlineCreate


EXTRACTION_SYSTEM_PROMPT = """你是一位小说创作助手。分析以下头脑风暴对话，提取其中有价值的创作素材。
将其归类为：设定条目（人物/世界观/组织/地理/事件等）、大纲节点（情节/章节方向）、灵感想法。

输出 JSON 格式：
{
  "settings": [{"category": "人物", "name": "...", "summary": "...", "content": "...", "weight": 7}],
  "outlines": [{"level": 2, "title": "...", "summary": "..."}],
  "ideas": [{"title": "...", "content": "..."}]
}

注意：
- 只提取对话中真正出现的内容，不要编造
- 设定条目要有明确的名称和分类
- 大纲节点应该是可落地的章节方向
- weight 1-10，越核心越高"""


class BrainstormService:
    """Stateless chat service for brainstorming conversations."""

    SYSTEM_PROMPT = "你是一位创意策划顾问。帮助作者拓展思路、激发灵感。输出应具有发散性和启发性，而非结论性。回答使用中文。"

    @staticmethod
    async def chat(db: Session, messages: list[dict], project_id: str | None = None) -> str:
        """Send full message history to LLM and return assistant reply."""
        adapter = get_adapter(db)

        if not messages or messages[0].get("role") != "system":
            messages = [{"role": "system", "content": BrainstormService.SYSTEM_PROMPT}] + messages

        if project_id:
            builder = ContextBuilder(db)
            from app.services.project_service import ProjectService
            project = ProjectService.get(db, project_id)
            if project:
                ctx_messages = builder.build("brainstorm", project_id, request="")
                for m in ctx_messages:
                    if m["role"] == "system":
                        messages[0]["content"] += "\n\n" + m["content"]

        response = await adapter.generate(messages, temperature=0.9, max_tokens=2048)
        record_usage(db, adapter.model, response.usage, scenario="brainstorm_chat")
        return response.content

    @staticmethod
    async def extract(db: Session, messages: list[dict]) -> dict:
        """Send conversation to LLM and get structured extraction of settings/outlines/ideas."""
        adapter = get_adapter(db)

        conv_text = ""
        for m in messages:
            if m["role"] == "user":
                conv_text += f"\n用户: {m['content']}\n"
            elif m["role"] == "assistant":
                conv_text += f"\n助手: {m['content']}\n"

        extraction_messages = [
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": f"以下是一段头脑风暴对话，请提取其中的创作素材：\n\n{conv_text[:8000]}"}
        ]
        response = await adapter.generate(extraction_messages, temperature=0.3, max_tokens=2048)
        record_usage(db, adapter.model, response.usage, scenario="brainstorm_extract")

        try:
            result = json.loads(response.content)
            return {
                "settings": result.get("settings", []),
                "outlines": result.get("outlines", []),
                "ideas": result.get("ideas", []),
            }
        except (json.JSONDecodeError, ValueError):
            return {"settings": [], "outlines": [], "ideas": []}

    @staticmethod
    def confirm_save(db: Session, project_id: str, data: dict, raw_messages: list[dict]) -> dict:
        """Write confirmed extractions to DB."""
        saved = {"settings": 0, "outlines": 0, "ideas": 0}

        for s in data.get("settings", []):
            setting_data = SettingCreate(
                project_id=project_id,
                category=s.get("category", "自定义"),
                name=s.get("name", "未命名"),
                summary=s.get("summary", ""),
                content=s.get("content", ""),
                weight=s.get("weight", 5),
            )
            SettingService.create(db, setting_data)
            saved["settings"] += 1

        for o in data.get("outlines", []):
            outline_data = OutlineCreate(
                project_id=project_id,
                level=o.get("level", 2),
                title=o.get("title", "未命名"),
                summary=o.get("summary", ""),
            )
            OutlineService.create(db, outline_data)
            saved["outlines"] += 1

        import json as j
        IdeaService.create(
            db,
            project_id=project_id,
            title=data.get("title", "头脑风暴记录"),
            content=j.dumps(raw_messages, ensure_ascii=False),
            source="brainstorm",
        )
        saved["ideas"] += 1
        return saved
