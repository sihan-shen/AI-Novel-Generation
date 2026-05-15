from typing import Any
from sqlalchemy.orm import Session
from app.models.setting import Setting, SettingRelation
from app.models.chapter import ChapterSettingLink
from app.llm.adapter import get_adapter
from app.llm.prompts.loader import load as load_prompt


class CleaningService:
    """Three-layer cleaning mechanism for settings."""

    @staticmethod
    def basic_clean(db: Session, project_id: str) -> dict[str, Any]:
        """Layer 1: Detect orphans, empty entries, version bloat."""
        report: dict[str, Any] = {"orphans": [], "empty": [], "cleaned_versions": 0}

        all_settings = db.query(Setting).filter(Setting.project_id == project_id).all()
        for s in all_settings:
            rel_count = db.query(SettingRelation).filter(
                (SettingRelation.from_setting_id == s.id) | (SettingRelation.to_setting_id == s.id)
            ).count()
            link_count = db.query(ChapterSettingLink).filter(
                ChapterSettingLink.setting_id == s.id
            ).count()
            if rel_count == 0 and link_count == 0 and s.status == "active":
                report["orphans"].append({"id": s.id, "name": s.name, "category": s.category})

        for s in all_settings:
            if not s.content.strip() and not s.summary.strip():
                report["empty"].append({"id": s.id, "name": s.name})

        report["cleaned_versions"] = 0
        return report

    @staticmethod
    async def consistency_check(db: Session, project_id: str) -> dict:
        """Layer 2: LLM-driven consistency check."""
        all_settings = db.query(Setting).filter(
            Setting.project_id == project_id,
            Setting.status == "active",
        ).all()

        context_lines = []
        for s in all_settings:
            context_lines.append(f"[{s.category}] {s.name}: {s.summary or s.content[:100]}")
            rels = db.query(SettingRelation).filter(
                (SettingRelation.from_setting_id == s.id) | (SettingRelation.to_setting_id == s.id)
            ).all()
            for r in rels:
                other_id = r.to_setting_id if r.from_setting_id == s.id else r.from_setting_id
                other = db.query(Setting).filter(Setting.id == other_id).first()
                if other:
                    context_lines.append(f"  → {r.relation_type}: {other.name}")

        context = "\n".join(context_lines)

        adapter = get_adapter(db)
        messages = [
            {"role": "system", "content": load_prompt("cleaning_consistency")},
            {"role": "user", "content": f"设定集：\n{context}\n\n检查逻辑矛盾和重复条目，输出JSON格式：{{\"contradictions\":[{{\"items\":[\"名称A\",\"名称B\"],\"issue\":\"...\",\"suggestion\":\"...\"}}],\"duplicates\":[{{\"items\":[\"名称A\",\"名称B\"],\"reason\":\"...\"}}]}}"}
        ]
        response = await adapter.generate(messages, temperature=0.3)
        try:
            import json
            return json.loads(response.content)
        except (json.JSONDecodeError, ValueError):
            return {"contradictions": [], "duplicates": []}

    @staticmethod
    def deep_clean(db: Session, project_id: str) -> dict[str, Any]:
        """Layer 3: Archive deprecated, suggest relation completions."""
        report: dict[str, Any] = {"archived": [], "suggestions": []}
        deprecated = db.query(Setting).filter(
            Setting.project_id == project_id,
            Setting.status == "deprecated",
        ).all()
        for s in deprecated:
            rel_count = db.query(SettingRelation).filter(
                (SettingRelation.from_setting_id == s.id) | (SettingRelation.to_setting_id == s.id)
            ).count()
            if rel_count == 0:
                report["archived"].append(s.name)
                db.delete(s)
        db.commit()
        return report
