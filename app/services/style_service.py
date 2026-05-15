import json
from sqlalchemy.orm import Session
from app.models.style import Style
from app.llm.adapter import get_adapter
from app.llm.prompts.loader import load as load_prompt


class StyleService:
    @staticmethod
    def create(db: Session, name: str, source: str = "", source_text: str = "", analysis: str = "{}", tags: str = "[]") -> Style:
        style = Style(name=name, source=source, source_text=source_text, analysis=analysis, tags=tags)
        db.add(style)
        db.commit()
        db.refresh(style)
        return style

    @staticmethod
    def list_all(db: Session) -> list[Style]:
        return db.query(Style).order_by(Style.created_at.desc()).all()

    @staticmethod
    def get(db: Session, style_id: str) -> Style | None:
        return db.query(Style).filter(Style.id == style_id).first()

    @staticmethod
    def delete(db: Session, style_id: str) -> bool:
        style = StyleService.get(db, style_id)
        if not style:
            return False
        db.delete(style)
        db.commit()
        return True

    @staticmethod
    def set_project_styles(db: Session, project_id: str, style_weights: list[dict]) -> None:
        """Set style weights for a project. style_weights = [{"style_id": "...", "weight": 0.7}, ...]"""
        from app.models.style import ProjectStyleLink
        db.query(ProjectStyleLink).filter(ProjectStyleLink.project_id == project_id).delete()
        for sw in style_weights:
            link = ProjectStyleLink(project_id=project_id, style_id=sw["style_id"], weight=sw.get("weight", 1.0))
            db.add(link)
        db.commit()

    @staticmethod
    async def analyze_text(db: Session, text: str) -> str:
        """Send text to LLM for style analysis."""
        adapter = get_adapter(db)
        messages = [
            {"role": "system", "content": load_prompt("style_analysis")},
            {"role": "user", "content": f"请分析以下文本的文风特征：\n\n{text}\n\n输出JSON格式：{{\"vocabulary\":\"\",\"rhythm\":\"\",\"rhetoric\":\"\",\"tone\":\"\",\"dialogue\":\"\",\"pov\":\"\"}}"}
        ]
        response = await adapter.generate(messages, temperature=0.3)
        return response.content

    @staticmethod
    async def smart_slice(db: Session, text: str) -> list[dict]:
        """Use LLM to identify representative style slices from long text."""
        adapter = get_adapter(db)
        messages = [
            {"role": "system", "content": load_prompt("style_slice")},
            {"role": "user", "content": f'请从以下文本中选出3-5个最能代表作者文风的段落（每段200-500字），覆盖不同类型的描写（叙事、环境、心理等）。按重要度排序，每个切片附推荐理由。\n\n文本：\n\n{text[:8000]}\n\n输出JSON格式：{{"slices":[{{"index":1,"text":"...","type":"...","reason":"...","stars":5}}]}}'}
        ]
        response = await adapter.generate(messages, temperature=0.3)
        try:
            result = json.loads(response.content)
            return result.get("slices", [])
        except json.JSONDecodeError:
            return [{"text": text[:500], "reason": "全文切片", "stars": 3}]
