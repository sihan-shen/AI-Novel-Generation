"""Setting Manager Agent tool handlers."""

import json
from sqlalchemy.orm import Session
from app.services.setting_service import SettingService
from app.schemas.setting import SettingCreate, SettingUpdate, SettingRelationCreate
from app.models.setting import Setting


def search_settings(db: Session, project_id: str, keywords: str = "", category: str | None = None) -> str:
    """Search settings by keywords and optional category."""
    all_settings = SettingService.list_by_project(db, project_id, category=category)
    matched = []
    kw_lower = keywords.lower() if keywords else ""
    for s in all_settings:
        if s.status != "active":
            continue
        if kw_lower and kw_lower not in f"{s.name} {s.summary or ''} {s.content or ''}".lower():
            continue
        matched.append({"id": s.id, "category": s.category, "name": s.name, "key": s.key, "summary": s.summary or "", "weight": s.weight})
    return json.dumps(matched, ensure_ascii=False)


def get_setting_detail(db: Session, setting_id: str) -> str:
    s = SettingService.get(db, setting_id)
    if not s:
        return json.dumps({"error": "Setting not found"})
    relations = SettingService.get_relations(db, setting_id)
    return json.dumps({
        "id": s.id, "category": s.category, "name": s.name, "key": s.key,
        "summary": s.summary or "", "content": s.content or "", "weight": s.weight,
        "status": s.status, "tags": s.tags,
        "relations": [{"id": r.id, "from": r.from_setting_id, "to": r.to_setting_id, "type": r.relation_type, "desc": r.description} for r in relations],
    }, ensure_ascii=False)


def get_related_settings(db: Session, setting_id: str) -> str:
    s = SettingService.get(db, setting_id)
    if not s:
        return json.dumps([])
    relations = SettingService.get_relations(db, setting_id)
    related_ids = set()
    for r in relations:
        other = r.to_setting_id if r.from_setting_id == setting_id else r.from_setting_id
        related_ids.add(other)
    related = []
    for rid in related_ids:
        rel_s = SettingService.get(db, rid)
        if rel_s and rel_s.status == "active":
            related.append({"id": rel_s.id, "name": rel_s.name, "category": rel_s.category, "summary": rel_s.summary or ""})
    return json.dumps(related, ensure_ascii=False)


def propose_setting(
    db: Session, project_id: str, category: str, name: str, key: str,
    summary: str = "", content: str = "", weight: int = 5, tags: str = "[]",
    write_mode: str = "suggest", task_id: str | None = None, blackboard=None,
) -> str:
    """Propose creating or updating a setting."""
    if write_mode == "suggest":
        if blackboard:
            blackboard.emit_event({
                "type": "pending_suggestion", "id": f"sug-setting-{key}",
                "tool": "propose_setting",
                "summary": f"建议{'更新' if _get_by_key(db, project_id, key) else '新增'}设定：{name}",
                "detail": {"category": category, "name": name, "key": key, "summary": summary[:200]},
            })
        return json.dumps({"status": "suggested", "name": name}, ensure_ascii=False)

    existing = _get_by_key(db, project_id, key)
    if existing:
        SettingService.update(db, existing.id, SettingUpdate(category=category, name=name, summary=summary, content=content, weight=weight, tags=tags))
        existing.proposed_by_type = "agent"
        existing.proposed_by_task_id = task_id
        db.commit()
        return json.dumps({"status": "updated", "setting_id": existing.id}, ensure_ascii=False)

    data = SettingCreate(project_id=project_id, category=category, name=name, key=key, summary=summary, content=content, weight=weight, tags=tags)
    new_s = SettingService.create(db, data)
    new_s.proposed_by_type = "agent"
    new_s.proposed_by_task_id = task_id
    db.commit()
    return json.dumps({"status": "created", "setting_id": new_s.id}, ensure_ascii=False)


def detect_conflicts(db: Session, project_id: str, new_setting_ids: list[str]) -> str:
    return json.dumps({"conflicts": []}, ensure_ascii=False)


def resolve_conflict(db: Session, conflict_desc: str, resolution: str, write_mode: str = "suggest") -> str:
    return json.dumps({"status": write_mode, "resolution": resolution}, ensure_ascii=False)


def link_settings(db: Session, from_setting_id: str, to_setting_id: str, relation_type: str, description: str = "") -> str:
    data = SettingRelationCreate(from_setting_id=from_setting_id, to_setting_id=to_setting_id, relation_type=relation_type, description=description)
    rel = SettingService.add_relation(db, data)
    return json.dumps({"status": "created", "relation_id": rel.id}, ensure_ascii=False)


def _get_by_key(db: Session, project_id: str, key: str) -> Setting | None:
    return db.query(Setting).filter(Setting.project_id == project_id, Setting.key == key).first()
