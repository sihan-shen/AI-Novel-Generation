"""Agent action routes: confirm, cancel, pending-actions, tasks."""

from __future__ import annotations

import logging

from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.models.agent_message import AgentMessage
from app.models.agent_task import AgentTask
from app.routers.agent.models import CancelRequest, ConfirmRequest
from app.routers.agent.shared import (
    _confirm_outcomes,
    _pending_confirms,
    _running_orchestrators,
    get_active_task,
)
from app.schemas.response import APIResponse

logger = logging.getLogger(__name__)


async def confirm_action_handler(
    project_id: str, body: ConfirmRequest
) -> JSONResponse | APIResponse[dict]:
    """Handle user response to a confirm request."""
    event = _pending_confirms.get(body.confirm_id)
    if event is None:
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": "Unknown or expired confirm_id"},
        )
    _confirm_outcomes[body.confirm_id] = {
        "action": body.action,
        "modification": body.modification,
    }
    event.set()
    _pending_confirms.pop(body.confirm_id, None)
    return APIResponse(
        data={"status": "ok", "message": f"Action '{body.action}' applied"}
    )


async def cancel_chat_handler(
    project_id: str, db: Session, body: CancelRequest | None = None
) -> APIResponse[dict]:
    """Request cancellation of the currently running orchestrator for a project."""
    active_task = get_active_task(db, project_id)
    if active_task is None:
        return APIResponse(data={"status": "ok", "message": "No active task"})
    orch = _running_orchestrators.get(active_task.id)
    if orch is None:
        return APIResponse(data={"status": "ok", "message": "No active task"})
    orch.cancel()
    return APIResponse(data={"status": "ok", "message": "Cancellation requested"})


async def pending_actions_handler(
    project_id: str, db: Session
) -> APIResponse[dict]:
    """Return pending confirm actions for a project."""
    task = (
        db.query(AgentTask)
        .filter(
            AgentTask.project_id == project_id,
            AgentTask.status == "waiting_user",
        )
        .first()
    )
    actions = []
    if task:
        pending_msgs = (
            db.query(AgentMessage)
            .filter(
                AgentMessage.task_id == task.id,
                AgentMessage.message_type == "confirm_request",
            )
            .all()
        )
        actions = [{"id": m.id, "summary": m.content[:200]} for m in pending_msgs]
    return APIResponse(
        data={
            "has_pending": bool(task) or bool(_pending_confirms),
            "task_id": task.id if task else None,
            "actions": actions,
            "confirm_ids": list(_pending_confirms.keys()),
        }
    )


async def list_tasks_handler(project_id: str, db: Session) -> APIResponse[dict]:
    """List recent agent tasks for a project."""
    tasks = (
        db.query(AgentTask)
        .filter(AgentTask.project_id == project_id)
        .order_by(AgentTask.created_at.desc())
        .limit(20)
        .all()
    )
    return APIResponse(
        data={
            "tasks": [
                {
                    "id": t.id,
                    "task_type": t.task_type,
                    "status": t.status,
                    "total_steps": t.total_steps,
                    "total_tokens": t.total_tokens,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                    "completed_at": (
                        t.completed_at.isoformat() if t.completed_at else None
                    ),
                }
                for t in tasks
            ]
        }
    )
