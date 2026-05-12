from sqlalchemy.orm import Session
from app.llm.context_builder import ContextBuilder
from app.llm.adapter import get_adapter, record_usage


class BrainstormService:
    @staticmethod
    async def brainstorm(db: Session, project_id: str | None, mode: str, query: str) -> str:
        """Execute a brainstorming session."""
        adapter = get_adapter()

        if mode == "free":
            messages = [
                {"role": "system", "content": "你是一位创意策划顾问。帮助作者拓展思路、激发灵感。"},
                {"role": "user", "content": f"请围绕以下主题进行头脑风暴，提供多个创意方向：\n\n{query}"}
            ]
        elif mode == "context" and project_id:
            builder = ContextBuilder(db)
            messages = builder.build("brainstorm", project_id, request=query)
        elif mode == "directed":
            messages = [
                {"role": "system", "content": "你是一位创意策划顾问。帮助作者拓展思路、激发灵感。"},
                {"role": "user", "content": f"方向：{query}\n\n请深入探讨这个方向，提供具体可用的创意。"}
            ]
        else:
            return "请提供有效的模式或项目上下文。"

        response = await adapter.generate(messages, temperature=0.9, max_tokens=2048)
        record_usage(db, adapter.model, response.usage, scenario=f"brainstorm_{mode}")
        return response.content
