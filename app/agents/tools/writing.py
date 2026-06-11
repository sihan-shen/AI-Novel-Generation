"""Writer Agent tool handlers."""

import json
from sqlalchemy.orm import Session
from app.services.setting_service import SettingService
from app.services.outline_service import OutlineService
from app.services.chapter_service import ChapterService
from app.schemas.chapter import ChapterCreate


def lookup_settings(db: Session, keywords: list[str], project_id: str) -> str:
    """Search settings by keywords."""
    all_settings = SettingService.list_by_project(db, project_id)
    matched = []
    for s in all_settings:
        if s.status != "active":
            continue
        full_text = f"{s.name} {s.summary or ''} {s.content or ''} {s.tags or ''}"
        for kw in keywords:
            if kw.lower() in full_text.lower():
                matched.append({
                    "id": s.id, "category": s.category, "name": s.name,
                    "key": s.key, "summary": s.summary or "", "weight": s.weight,
                    "content_preview": (s.content or "")[:500],
                })
                break
    return json.dumps(matched, ensure_ascii=False)


def get_outline_context(db: Session, project_id: str, outline_id: str | None = None) -> str:
    """Get outline tree context."""
    items = OutlineService.get_tree(db, project_id)
    if outline_id:
        target = next((i for i in items if i.id == outline_id), None)
        if target:
            parent = next((i for i in items if i.id == target.parent_id), None)
            siblings = [i for i in items if i.parent_id == target.parent_id and i.id != target.id]
            children = [i for i in items if i.parent_id == target.id]
            return json.dumps({
                "current": _outline_dict(target),
                "parent": _outline_dict(parent) if parent else None,
                "siblings": [_outline_dict(s) for s in siblings],
                "children": [_outline_dict(c) for c in children],
            }, ensure_ascii=False)
    return json.dumps([_outline_dict(i) for i in items], ensure_ascii=False)


def get_recent_chapters(db: Session, project_id: str, count: int = 3) -> str:
    """Get the most recent N chapters."""
    chapters = ChapterService.list_by_project(db, project_id)
    recent = chapters[-count:] if len(chapters) > count else chapters
    return json.dumps([
        {"id": c.id, "title": c.title, "content_preview": (c.content or "")[:300], "word_count": c.word_count}
        for c in recent
    ], ensure_ascii=False)


def get_style_guide(db: Session, project_id: str) -> str:
    """Get the project's configured style guide."""
    from app.models.style import ProjectStyleLink
    from app.services.style_service import StyleService
    links = db.query(ProjectStyleLink).filter(ProjectStyleLink.project_id == project_id).all()
    styles = []
    for link in links:
        style = StyleService.get(db, link.style_id)
        if style:
            styles.append({"name": style.name, "analysis": style.analysis or "{}", "weight": link.weight})
    return json.dumps(styles, ensure_ascii=False)


def write_chapter(
    db: Session, project_id: str, outline_id: str,
    title: str, content: str, sort_order: int = 1,
    write_mode: str = "draft", task_id: str | None = None,
    blackboard=None,
) -> str:
    """Write a chapter. Draft mode upserts on outline_id."""
    if write_mode == "suggest":
        if blackboard:
            blackboard.emit_event({
                "type": "pending_suggestion", "id": f"sug-{outline_id}",
                "tool": "write_chapter",
                "summary": f"建议章节：{title} ({len(content)}字)",
                "detail": {"title": title, "content_preview": content[:300], "outline_id": outline_id},
            })
        return json.dumps({"status": "suggested", "title": title, "word_count": len(content)}, ensure_ascii=False)

    from app.models.chapter import Chapter
    existing = db.query(Chapter).filter(
        Chapter.project_id == project_id, Chapter.outline_id == outline_id,
    ).first()

    if existing and write_mode == "draft":
        existing.title = title
        existing.content = content
        existing.word_count = len(content)
        existing.generated_by_type = "agent"
        existing.generated_by_task_id = task_id
        db.commit()
        return json.dumps({"status": "updated", "chapter_id": existing.id, "word_count": len(content)}, ensure_ascii=False)

    ch = Chapter(
        project_id=project_id, outline_id=outline_id, title=title, content=content,
        sort_order=sort_order, status="published" if write_mode == "direct" else "draft",
        generated_by_type="agent", generated_by_task_id=task_id, generation_prompt="",
    )
    ch.word_count = len(content)
    db.add(ch)
    db.commit()
    db.refresh(ch)
    return json.dumps({"status": "created", "chapter_id": ch.id, "word_count": ch.word_count}, ensure_ascii=False)


def update_outline_status(db: Session, outline_id: str, status: str = "done", write_mode: str = "draft") -> str:
    """Update outline node status."""
    from app.schemas.outline import OutlineUpdate
    OutlineService.update(db, outline_id, OutlineUpdate(status=status))
    return json.dumps({"status": "updated", "outline_id": outline_id}, ensure_ascii=False)


def _outline_dict(item) -> dict:
    return {"id": item.id, "parent_id": item.parent_id, "level": item.level, "sort_order": item.sort_order, "title": item.title, "summary": item.summary or "", "status": item.status}
