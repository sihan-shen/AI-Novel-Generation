import json
from sqlalchemy.orm import Session
from app.models.setting import Setting, SettingRelation
from app.schemas.setting import SettingCreate, SettingUpdate, SettingRelationCreate


CATEGORIES = ["世界观", "人物", "组织", "地理", "魔法/科技体系", "事件", "物品", "自定义"]


class SettingService:
    @staticmethod
    def create(db: Session, data: SettingCreate) -> Setting:
        obj = Setting(
            project_id=data.project_id, category=data.category, name=data.name,
            summary=data.summary, content=data.content,
            structured_data=data.structured_data, weight=data.weight,
            key=data.key or data.name, tags=data.tags,
        )
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def get(db: Session, setting_id: str) -> Setting | None:
        return db.query(Setting).filter(Setting.id == setting_id).first()

    @staticmethod
    def list_by_project(db: Session, project_id: str, category: str | None = None) -> list[Setting]:
        q = db.query(Setting).filter(Setting.project_id == project_id)
        if category:
            q = q.filter(Setting.category == category)
        return q.order_by(Setting.sort_order, Setting.name).all()

    @staticmethod
    def update(db: Session, setting_id: str, data: SettingUpdate) -> Setting | None:
        obj = SettingService.get(db, setting_id)
        if not obj:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(obj, field, value)
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def reorder(db: Session, items: list[dict]) -> None:
        for item in items:
            db.query(Setting).filter(Setting.id == item["id"]).update(
                {"sort_order": item["sort_order"]}
            )
        db.commit()

    @staticmethod
    def delete(db: Session, setting_id: str) -> bool:
        obj = SettingService.get(db, setting_id)
        if not obj:
            return False
        db.delete(obj)
        db.commit()
        return True

    @staticmethod
    def add_relation(db: Session, data: SettingRelationCreate) -> SettingRelation:
        rel = SettingRelation(
            from_setting_id=data.from_setting_id,
            to_setting_id=data.to_setting_id,
            relation_type=data.relation_type,
            description=data.description,
        )
        db.add(rel)
        db.commit()
        db.refresh(rel)
        return rel

    @staticmethod
    def remove_relation(db: Session, relation_id: str) -> bool:
        rel = db.query(SettingRelation).filter(SettingRelation.id == relation_id).first()
        if not rel:
            return False
        db.delete(rel)
        db.commit()
        return True

    @staticmethod
    def get_relations(db: Session, setting_id: str) -> list[SettingRelation]:
        return db.query(SettingRelation).filter(
            (SettingRelation.from_setting_id == setting_id) | (SettingRelation.to_setting_id == setting_id)
        ).all()

    @staticmethod
    def build_llm_context(db: Session, project_id: str, related_ids: list[str] | None = None) -> str:
        """Build a condensed settings summary for LLM context."""
        settings = SettingService.list_by_project(db, project_id)
        lines = ["=== 设定集摘要 ==="]
        for s in settings:
            if s.status != "active":
                continue
            weight_tag = "高" if s.weight >= 7 else "中" if s.weight >= 4 else "低"
            tag_str = f"[权重{weight_tag}]"
            lines.append(f"{tag_str} {s.category}: {s.name} (key: {s.key})")
        lines.append("")
        if related_ids:
            lines.append("=== 详细设定（相关条目） ===")
            for sid in related_ids:
                s = SettingService.get(db, sid)
                if s and s.status == "active":
                    lines.append(f"## {s.category}：{s.name} [{s.key}]")
                    lines.append(s.summary or (s.content[:200] if s.content else ""))
                    lines.append("")
        return "\n".join(lines)
