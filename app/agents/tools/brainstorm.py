"""Brainstorm Agent tool handlers."""

import json
import uuid

from sqlalchemy.orm import Session


def save_inspiration(
    db: Session,
    task_id: str,
    insp_type: str,
    title: str,
    content: str,
    category: str = "",
) -> str:
    """Propose saving a brainstorm result. Accumulates in task.metadata pending_inspirations.

    Args:
        insp_type: "idea" | "setting" | "outline"
        title: Short descriptive title
        content: The inspiration content
        category: Optional category (e.g. "角色", "世界观")
    """
    from app.models.agent_task import AgentTask

    task = db.query(AgentTask).filter(AgentTask.id == task_id).first()
    if not task:
        return json.dumps({"status": "error", "message": "Task not found"}, ensure_ascii=False)

    pending = task.task_metadata.get("pending_inspirations", [])
    proposal = {
        "id": str(uuid.uuid4())[:8],
        "type": insp_type,
        "title": title,
        "content": content[:2000],
        "category": category,
        "created_at": None,  # Will be set at save time
    }
    pending.append(proposal)
    task.update_task_metadata(pending_inspirations=pending)
    db.commit()

    return json.dumps({
        "status": "proposed",
        "proposal_id": proposal["id"],
        "message": f"灵感「{title}」已暂存，脑暴结束后可确认保存",
        "pending_count": len(pending),
    }, ensure_ascii=False)


def list_pending_inspirations(db: Session, task_id: str) -> str:
    """List all pending inspirations for the current brainstorm session."""
    from app.models.agent_task import AgentTask

    task = db.query(AgentTask).filter(AgentTask.id == task_id).first()
    if not task:
        return json.dumps([], ensure_ascii=False)

    pending = task.task_metadata.get("pending_inspirations", [])
    return json.dumps(pending, ensure_ascii=False)
