import json
from sqlalchemy.orm import Session
from app.llm.context_builder import ContextBuilder
from app.llm.adapter import get_adapter, record_usage
from app.services.setting_service import SettingService
from app.services.outline_service import OutlineService
from app.services.idea_service import IdeaService
from app.schemas.setting import SettingCreate
from app.schemas.outline import OutlineCreate


EXTRACTION_SYSTEM_PROMPT = """你是一位小说创作助理。分析以下头脑风暴对话，提取其中可用于创作的素材。

## 提取类别

### 设定条目 (settings)
适合存入设定集的内容：人物、组织、世界观规则、地理地点、物品、事件等。
每个条目需有明确的：分类(category)、名称(name)、概要(summary)、详细描述(content)、重要度(weight 1-10)。
- 人物包含：身份、性格、目标、关系
- 组织包含：性质、宗旨、成员
- 世界观包含：规则、限制、特点

### 大纲节点 (outlines)
适合写入大纲的情节方向或章节建议。
每个节点需有：层级(level: 2=章/3=节)、标题(title)、概要(summary)。

### 灵感想法 (ideas)
有价值的零散创意，尚不足以形成完整设定或大纲。

## 输出格式
{
  "settings": [{"category": "人物", "name": "...", "summary": "...", "content": "...", "weight": 7}],
  "outlines": [{"level": 2, "title": "...", "summary": "..."}],
  "ideas": [{"title": "...", "content": "..."}]
}

## 注意事项
- 只提取对话中真正出现的内容，不要编造或添加
- 设定条目必须可独立理解，名称要具体
- 如果某类没有提取到，返回空数组即可"""


class BrainstormService:
    """Stateless chat service for brainstorming conversations."""

    SYSTEM_PROMPT = """你是一位专业的小说创作顾问，擅长帮助作者拓展创意、完善构思。

## 你的能力
- 基于作者提供的故事方向，发散多种可能的剧情走向
- 帮助塑造立体的人物（动机、弧光、关系）
- 设计有张力的情节结构和冲突
- 构建自洽的世界观和设定体系
- 对作者已有的构思提供建设性反馈和深化建议

## 交流原则
- 回答使用中文，语气友好且专业
- 输出结构化：分点列出、层次分明
- 提供具体可操作的创意，而非空泛的评价
- 适当追问和引导，帮助作者深入思考
- 每次围绕一个主题展开，避免信息过载"""

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
