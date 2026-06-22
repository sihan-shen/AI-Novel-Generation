"""Setting Manager Agent tool handlers."""

import asyncio
import contextlib
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.llm.adapter import get_adapter, record_usage
from app.models.agent_task import AgentTask
from app.models.setting import Setting
from app.schemas.setting import SettingCreate, SettingRelationCreate, SettingUpdate
from app.services.setting_service import SettingService

_resolved_conflicts_fallback: list[dict] = []
_llm_pool = ThreadPoolExecutor(max_workers=1)

logger = logging.getLogger(__name__)


def _sync_generate(adapter, messages, **kwargs):
    """Run adapter.generate() from synchronous code, with thread-pool timeout.

    Uses a dedicated ThreadPoolExecutor so that on TimeoutError the future
    is cancelled and the worker thread is reclaimed — unlike the raw
    threading.Thread + t.join(timeout=60) pattern which leaks the thread.
    """
    if not asyncio.iscoroutinefunction(adapter.generate):
        return adapter.generate(messages, **kwargs)

    async def _gen():
        return await adapter.generate(messages, **kwargs)

    try:
        asyncio.get_running_loop()
        return _llm_pool.submit(asyncio.run, _gen()).result(timeout=30)
    except RuntimeError:
        return asyncio.run(_gen())


def search_settings(db: Session, project_id: str, keywords: str = "", category: str | None = None) -> str:  # noqa: E501
    all_settings = SettingService.list_by_project(db, project_id, category=category)
    matched = []
    kw_lower = keywords.lower() if keywords else ""
    for s in all_settings:
        if s.status != "active":
            continue
        if kw_lower and kw_lower not in f"{s.name} {s.summary or ''} {s.content or ''}".lower():
            continue
        matched.append({"id": s.id, "category": s.category, "name": s.name, "key": s.key, "summary": s.summary or "", "weight": s.weight})  # noqa: E501
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
        "relations": [{"id": r.id, "from": r.from_setting_id, "to": r.to_setting_id, "type": r.relation_type, "desc": r.description} for r in relations],  # noqa: E501
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
        rel_s = SettingService.get(db, rid)  # type: ignore[arg-type]
        if rel_s and rel_s.status == "active":
            related.append({"id": rel_s.id, "name": rel_s.name, "category": rel_s.category, "summary": rel_s.summary or ""})  # noqa: E501
    return json.dumps(related, ensure_ascii=False)


def propose_setting(
    db: Session, project_id: str, category: str, name: str, key: str,
    summary: str = "", content: str = "", weight: int = 5, tags: str = "[]",
    write_mode: str = "suggest", task_id: str | None = None, blackboard=None,
) -> str:
    if write_mode == "suggest":
        if blackboard:
            blackboard.emit_event({
                "type": "pending_suggestion", "id": f"sug-setting-{key}",
                "tool": "propose_setting",
                "summary": f"建议{'更新' if _get_by_key(db, project_id, key) else '新增'}设定：{name}",  # noqa: E501
                "detail": {"category": category, "name": name, "key": key, "summary": summary[:200]},  # noqa: E501
            })
        return json.dumps({"status": "suggested", "name": name}, ensure_ascii=False)

    existing = _get_by_key(db, project_id, key)
    if existing:
        SettingService.update(
            db, str(existing.id),  # type: ignore[arg-type]
            SettingUpdate(
                category=category, name=name, summary=summary,
                content=content, weight=weight, tags=tags,
            ),
        )
        existing.proposed_by_type = "agent"  # type: ignore[assignment]
        existing.proposed_by_task_id = task_id  # type: ignore[assignment]
        db.commit()
        return json.dumps({"status": "updated", "setting_id": existing.id}, ensure_ascii=False)

    data = SettingCreate(project_id=project_id, category=category, name=name, key=key, summary=summary, content=content, weight=weight, tags=tags)  # noqa: E501
    new_s = SettingService.create(db, data)
    new_s.proposed_by_type = "agent"  # type: ignore[assignment]
    new_s.proposed_by_task_id = task_id  # type: ignore[assignment]
    db.commit()
    return json.dumps({"status": "created", "setting_id": new_s.id}, ensure_ascii=False)


def _detect_key_duplicates(
    new_settings: list[Setting], active_existing: list[Setting],
) -> list[dict]:
    """Detect settings that share the same key across new and existing sets."""
    seen_keys: dict[str, list[str]] = {}
    for s in new_settings:
        if s.key:
            seen_keys.setdefault(s.key, []).append(s.id)  # type: ignore[arg-type]
    for s in active_existing:
        if s.key:
            seen_keys.setdefault(s.key, []).append(s.id)  # type: ignore[arg-type]

    conflicts: list[dict] = []
    for key, ids in seen_keys.items():
        unique_ids = list(dict.fromkeys(ids))
        if len(unique_ids) > 1:
            conflicts.append({
                "id": f"dup-key-{key}",
                "desc": f"Duplicate key '{key}' across settings: {', '.join(unique_ids)}",
                "severity": "high",
                "setting_ids": unique_ids,
            })
    return conflicts


def _build_contradiction_prompt(
    new_settings: list[Setting], active_existing: list[Setting],
) -> str:
    """Build the LLM prompt for contradiction detection between two setting sets."""
    lines = [
        "Detect contradictions between the following new settings and existing active settings.",  # noqa: E501
        "",
        "=== New Settings ===",
    ]
    lines += [
        f"ID: {s.id} | Key: {s.key} | Name: {s.name} | Content: {s.content or s.summary or ''}"  # noqa: E501
        for s in new_settings
    ]
    lines += ["", "=== Existing Active Settings ==="]
    lines += [
        f"ID: {s.id} | Key: {s.key} | Name: {s.name} | Content: {s.content or s.summary or ''}"  # noqa: E501
        for s in active_existing
    ]
    lines += [
        "",
        'Return JSON only: {"conflicts":[{"id":"...","desc":"...","severity":"low|medium|high","setting_ids":["..."]}]}. '  # noqa: E501
        'If no contradictions, return {"conflicts":[]}.',
    ]
    return "\n".join(lines)


def _detect_llm_contradictions(
    db: Session, new_settings: list[Setting],
    active_existing: list[Setting], project_id: str,
) -> list[dict]:
    """Use LLM to detect contradictions between new and existing settings."""
    if not new_settings or not active_existing:
        return []
    conflicts: list[dict] = []
    try:
        adapter = get_adapter(db)
        messages = [
            {"role": "system", "content": "You are a setting consistency checker. Respond with valid JSON only."},  # noqa: E501
            {"role": "user", "content": _build_contradiction_prompt(new_settings, active_existing)},
        ]
        response = _sync_generate(adapter, messages, temperature=0.3, max_tokens=1024)
        try:
            llm_result = json.loads(response.content)
            for c in llm_result.get("conflicts", []):
                if isinstance(c, dict) and "id" in c and "desc" in c:
                    conflicts.append({"id": c["id"], "desc": c["desc"],
                                      "severity": c.get("severity", "medium"),
                                      "setting_ids": c.get("setting_ids", [])})
        except (json.JSONDecodeError, AttributeError):
            pass
        with contextlib.suppress(Exception):
            record_usage(db, adapter.model, response.usage or {},
                         scenario="detect_conflicts", project_id=project_id)
    except Exception:
        logger.exception("_detect_llm_contradictions: LLM contradiction check failed")
    return conflicts


def detect_conflicts(db: Session, project_id: str, new_setting_ids: list[str]) -> str:
    try:
        new_settings = [
            s for sid in new_setting_ids if (s := SettingService.get(db, sid))
        ]
        existing_settings = SettingService.list_by_project(db, project_id)
    except Exception:
        logger.exception("detect_conflicts: Service calls failed")
        return json.dumps({"conflicts": []}, ensure_ascii=False)

    active_existing = [s for s in existing_settings if s.status == "active"]

    conflicts = (
        _detect_key_duplicates(new_settings, active_existing)
        + _detect_llm_contradictions(db, new_settings, active_existing, project_id)
    )
    return json.dumps({"conflicts": conflicts}, ensure_ascii=False)


def resolve_conflict(db: Session, conflict_desc: str, resolution: str, write_mode: str = "suggest") -> str:  # noqa: E501
    resolved_entry = {
        "conflict_desc": conflict_desc,
        "resolution": resolution,
        "resolved_at": datetime.now(UTC).isoformat(),
    }

    task = (
        db.query(AgentTask)
        .filter(AgentTask.status.in_(["running", "waiting_user"]))
        .order_by(AgentTask.created_at.desc())
        .first()
    )

    if task:
        resolved = task.task_metadata.get("resolved_conflicts", [])
        resolved.append(resolved_entry)
        task.update_task_metadata(resolved_conflicts=resolved)
        db.commit()
    else:
        _resolved_conflicts_fallback.append(resolved_entry)

    return json.dumps({
        "status": "resolved",
        "conflict_desc": conflict_desc,
        "resolution": resolution,
    }, ensure_ascii=False)


def link_settings(db: Session, from_setting_id: str, to_setting_id: str, relation_type: str, description: str = "") -> str:  # noqa: E501
    data = SettingRelationCreate(from_setting_id=from_setting_id, to_setting_id=to_setting_id, relation_type=relation_type, description=description)  # noqa: E501
    rel = SettingService.add_relation(db, data)
    return json.dumps({"status": "created", "relation_id": rel.id}, ensure_ascii=False)


def _get_by_key(db: Session, project_id: str, key: str) -> Setting | None:
    return db.query(Setting).filter(Setting.project_id == project_id, Setting.key == key).first()
