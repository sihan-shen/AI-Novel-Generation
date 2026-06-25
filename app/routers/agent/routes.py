"""Route registrations for agent endpoints — imported by __init__.py as a side-effect."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid

from fastapi import Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.llm.adapter import get_adapter
from app.models.agent_task import AgentTask
from app.schemas.response import APIResponse
from app.routers.agent.actions import (
    cancel_chat_handler,
    confirm_action_handler,
    list_tasks_handler,
    pending_actions_handler,
)
from app.routers.agent.brainstorm import (
    confirm_inspirations_handler,
    detect_intent,
    handle_brainstorm_flow,
)
from app.routers.agent.models import (
    CancelRequest,
    ChatRequest,
    ConfirmInspirationsRequest,
    ConfirmRequest,
)
from app.routers.agent.orchestration import _run_orchestrator_flow
from app.routers.agent.shared import (
    get_active_task,
    get_project_lock,
    router,
)
from app.routers.agent.stream import resume_events

logger = logging.getLogger(__name__)


@router.post("/chat/stream")
async def chat_stream(
    project_id: str,
    body: ChatRequest,
    resume_from: int = Query(0, description="Sequence number to resume from"),
    db: Session = Depends(get_db),
):
    async def event_stream():
        try:
            if resume_from > 0:
                async for event in resume_events(db, project_id, resume_from):
                    yield event
                return

            adapter = get_adapter(db)
            lock = get_project_lock(project_id)

            async with lock:
                active_task = get_active_task(db, project_id)

                if active_task and active_task.task_type == "brainstorm":
                    async for event in handle_brainstorm_flow(
                        db, adapter, active_task, body.message, project_id
                    ):
                        yield event
                    return

                if active_task is None:
                    if body.message.strip().startswith("/brainstorm"):
                        intent = "brainstorm"
                    else:
                        intent = await detect_intent(adapter, body.message)

                    if intent == "brainstorm":
                        from app.agents.autonomy import AutonomyConfig

                        task_obj = AgentTask(
                            id=str(uuid.uuid4()),
                            project_id=project_id,
                            task_type="brainstorm",
                            target_desc=body.message[:500],
                            autonomy_config=json.dumps(AutonomyConfig().to_dict()),
                            orchestrator_state="BRAINSTORMING",
                            status="running",
                        )
                        db.add(task_obj)
                        try:
                            db.commit()
                        except Exception:
                            logger.exception(
                                "Failed to create brainstorm task for project %s",
                                project_id,
                            )
                            db.rollback()
                            raise

                        yield f"event: agent_start\ndata: {json.dumps({'agent': 'brainstorm', 'task_id': task_obj.id}, ensure_ascii=False)}\n\n"  # noqa: E501

                        async for event in handle_brainstorm_flow(
                            db, adapter, task_obj, body.message, project_id
                        ):
                            yield event
                        return

            async for event in _run_orchestrator_flow(db, adapter, body, project_id):
                yield event
        except Exception as exc:
            logger.exception("SSE stream error for project %s", project_id)
            error_data = json.dumps(
                {"message": str(exc), "code": "stream_error"}, ensure_ascii=False
            )
            yield f"event: error\ndata: {error_data}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/chat/confirm", response_model=APIResponse[dict])
async def confirm_action(
    project_id: str,
    body: ConfirmRequest,
    db: Session = Depends(get_db),
):
    return await confirm_action_handler(project_id, body)


@router.post("/chat/cancel", response_model=APIResponse[dict])
async def cancel_chat(
    project_id: str,
    body: CancelRequest | None = None,
    db: Session = Depends(get_db),
):
    return await cancel_chat_handler(project_id, db, body)


@router.get("/pending-actions", response_model=APIResponse[dict])
async def pending_actions(project_id: str, db: Session = Depends(get_db)):
    return await pending_actions_handler(project_id, db)


@router.get("/tasks", response_model=APIResponse[dict])
async def list_tasks(project_id: str, db: Session = Depends(get_db)):
    return await list_tasks_handler(project_id, db)


@router.post("/inspirations/confirm", response_model=APIResponse[dict])
async def confirm_inspirations(
    project_id: str,
    body: ConfirmInspirationsRequest,
    db: Session = Depends(get_db),
):
    """Confirm and save selected inspirations from a completed brainstorm session."""
    return await confirm_inspirations_handler(project_id, body, db)
