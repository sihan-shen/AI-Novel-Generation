"""Agent router — page rendering + SSE streaming + task API."""

import asyncio
import json
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.llm.adapter import get_adapter
from app.models.agent_task import AgentTask
from app.models.agent_message import AgentMessage

router = APIRouter(prefix="/project/{project_id}/agent", tags=["agent"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


class ChatRequest(BaseModel):
    message: str
    chapter_outline_id: str | None = None
    target_words: int = 3000


class ConfirmRequest(BaseModel):
    confirm_id: str
    action: str  # 'approve' | 'reject' | 'modify'
    modification: str | None = None


@router.get("", response_class=HTMLResponse)
async def agent_page(request: Request, project_id: str, db: Session = Depends(get_db)):
    from app.services.project_service import ProjectService
    project = ProjectService.get(db, project_id)
    if not project:
        return HTMLResponse("Project not found", status_code=404)
    return templates.TemplateResponse(request, "agent/index.html", {"project": project})


@router.post("/chat/stream")
async def chat_stream(
    project_id: str,
    body: ChatRequest,
    resume_from: int = Query(0, description="Sequence number to resume from"),
    db: Session = Depends(get_db),
):
    from app.agents.blackboard import Blackboard
    from app.agents.autonomy import AutonomyConfig
    from app.agents.orchestrator import Orchestrator

    async def event_stream():
        # If resuming, replay past messages from agent_messages
        if resume_from > 0:
            task = db.query(AgentTask).filter(
                AgentTask.project_id == project_id,
                AgentTask.status.in_(["running", "waiting_user"]),
            ).order_by(AgentTask.created_at.desc()).first()
            if task:
                old_msgs = db.query(AgentMessage).filter(
                    AgentMessage.task_id == task.id,
                    AgentMessage.sequence >= resume_from,
                ).order_by(AgentMessage.sequence).all()
                for m in old_msgs:
                    event_data = json.loads(m.msg_metadata or "{}") if m.msg_metadata else {}
                    yield f"event: {m.message_type}\ndata: {json.dumps({'sequence': m.sequence, **event_data}, ensure_ascii=False)}\n\n"
                yield f"event: reconnect\ndata: {{\"status\": \"reconnected\", \"task_id\": \"{task.id}\"}}\n\n"
            else:
                yield "event: reconnect\ndata: {\"status\": \"no_active_task\"}\n\n"
            return

        # Normal execution path
        adapter = get_adapter(db)
        autonomy = AutonomyConfig()
        task = {"type": "write_chapter", "chapter_outline_id": body.chapter_outline_id, "target_words": body.target_words}
        blackboard = Blackboard(project_id=project_id, task=task, autonomy_config=autonomy)
        orch = Orchestrator(db=db, blackboard=blackboard, adapter=adapter)
        orch_task = asyncio.create_task(orch.run())
        seq = 0
        while not orch_task.done() or not blackboard.events.empty():
            try:
                event = await asyncio.wait_for(blackboard.events.get(), timeout=0.5)
                seq += 1
                event["sequence"] = seq
                yield f"event: {event['type']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
            except asyncio.TimeoutError:
                if orch_task.done():
                    break
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(
        event_stream(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@router.post("/chat/confirm")
async def confirm_action(
    project_id: str,
    body: ConfirmRequest,
    db: Session = Depends(get_db),
):
    """Handle user response to a confirm request."""
    task = db.query(AgentTask).filter(
        AgentTask.project_id == project_id,
        AgentTask.status == "waiting_user",
    ).first()

    if not task:
        return {"status": "error", "message": "No active task waiting for user input"}

    msg = AgentMessage(
        id=str(uuid.uuid4()),
        task_id=task.id,
        role="user",
        content=f"Confirm {body.confirm_id}: {body.action}",
        message_type="confirm_response",
        msg_metadata=json.dumps({"confirm_id": body.confirm_id, "action": body.action, "modification": body.modification}),
        sequence=999,
    )
    db.add(msg)
    db.commit()
    return {"status": "ok", "message": f"Action '{body.action}' recorded", "task_id": task.id}


@router.get("/pending-actions")
async def pending_actions(project_id: str, db: Session = Depends(get_db)):
    task = db.query(AgentTask).filter(
        AgentTask.project_id == project_id,
        AgentTask.status == "waiting_user",
    ).first()
    if not task:
        return {"has_pending": False, "actions": []}
    pending_msgs = db.query(AgentMessage).filter(
        AgentMessage.task_id == task.id,
        AgentMessage.message_type == "confirm_request",
    ).all()
    return {"has_pending": True, "task_id": task.id, "actions": [{"id": m.id, "summary": m.content[:200]} for m in pending_msgs]}


@router.get("/tasks")
async def list_tasks(project_id: str, db: Session = Depends(get_db)):
    from app.models.agent_task import AgentTask
    tasks = db.query(AgentTask).filter(AgentTask.project_id == project_id).order_by(AgentTask.created_at.desc()).limit(20).all()
    return {"tasks": [{"id": t.id, "task_type": t.task_type, "status": t.status, "total_steps": t.total_steps, "total_tokens": t.total_tokens, "created_at": t.created_at.isoformat() if t.created_at else None, "completed_at": t.completed_at.isoformat() if t.completed_at else None} for t in tasks]}
