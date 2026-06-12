"""Agent router — page rendering + SSE streaming + task API."""

import asyncio
import json
import uuid
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query, Request
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


class RollbackRequest(BaseModel):
    chapter_id: str


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

        # Normal execution path — create persisted AgentTask
        adapter = get_adapter(db)
        autonomy = AutonomyConfig()
        task_def = {"type": "write_chapter", "chapter_outline_id": body.chapter_outline_id, "target_words": body.target_words}
        task_obj = AgentTask(
            id=str(uuid.uuid4()),
            project_id=project_id,
            task_type="write_chapter",
            target_desc=body.message[:500],
            autonomy_config=json.dumps(autonomy.to_dict()),
            orchestrator_state="RUNNING",
            status="running",
        )
        db.add(task_obj)
        db.commit()
        task_id = task_obj.id

        blackboard = Blackboard(project_id=project_id, task=task_def, autonomy_config=autonomy)
        orch = Orchestrator(db=db, blackboard=blackboard, adapter=adapter, task_id=task_id)
        orch_task = asyncio.create_task(orch.run())
        seq = 0

        try:
            while not orch_task.done() or not blackboard.events.empty():
                try:
                    event = await asyncio.wait_for(blackboard.events.get(), timeout=0.5)
                    seq += 1
                    event["sequence"] = seq
                    yield f"event: {event['type']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"

                    # Persist each event as AgentMessage
                    content = event.get("text", event.get("summary", event.get("tool", "")))
                    msg = AgentMessage(
                        id=str(uuid.uuid4()),
                        task_id=task_id,
                        role="user" if event["type"] in ("user_message", "confirm_response") else "assistant",
                        content=str(content)[:2000],
                        message_type=event["type"],
                        msg_metadata=json.dumps(event, ensure_ascii=False),
                        sequence=seq,
                    )
                    db.add(msg)
                    db.commit()

                    # Update task progress periodically
                    if seq % 10 == 1:
                        task_obj.total_steps = seq
                        db.commit()
                except asyncio.TimeoutError:
                    if orch_task.done():
                        break
        finally:
            # Final state — capture orchestrator result
            final_state = blackboard.orchestrator_state
            task_obj.orchestrator_state = final_state
            task_obj.total_steps = seq
            task_obj.total_tokens = blackboard.cumulative_tokens
            if final_state in ("DONE", "CANCELLED", "IDLE"):
                task_obj.status = "completed" if final_state == "DONE" else "cancelled"
                task_obj.completed_at = datetime.utcnow()
            elif final_state == "WAITING_USER":
                task_obj.status = "waiting_user"
            try:
                task_obj.blackboard_snapshot = json.dumps(blackboard.to_snapshot(), ensure_ascii=False)
            except Exception:
                pass
            db.commit()

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
async def list_tasks(
    project_id: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    from sqlalchemy import func
    total = db.query(func.count(AgentTask.id)).filter(AgentTask.project_id == project_id).scalar()
    tasks = (
        db.query(AgentTask)
        .filter(AgentTask.project_id == project_id)
        .order_by(AgentTask.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    result = []
    for t in tasks:
        msg_count = db.query(func.count(AgentMessage.id)).filter(AgentMessage.task_id == t.id).scalar()
        summary = (t.target_desc or t.task_type)[:100]
        result.append({
            "id": t.id,
            "task_type": t.task_type,
            "status": t.status,
            "summary": summary,
            "orchestrator_state": t.orchestrator_state,
            "total_steps": t.total_steps,
            "total_tokens": t.total_tokens,
            "message_count": msg_count,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
        })
    return {"tasks": result, "total": total, "page": page, "per_page": per_page}


@router.get("/tasks/{task_id}/messages")
async def list_task_messages(task_id: str, db: Session = Depends(get_db)):
    task = db.query(AgentTask).filter(AgentTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    msgs = (
        db.query(AgentMessage)
        .filter(AgentMessage.task_id == task_id)
        .order_by(AgentMessage.sequence)
        .all()
    )
    return {
        "task_id": task_id,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "message_type": m.message_type,
                "msg_metadata": json.loads(m.msg_metadata) if m.msg_metadata else {},
                "sequence": m.sequence,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in msgs
        ],
    }


@router.post("/tasks/{task_id}/rerun")
async def rerun_task(task_id: str, project_id: str, db: Session = Depends(get_db)):
    """Re-run a completed task from its blackboard snapshot."""
    task = db.query(AgentTask).filter(AgentTask.id == task_id, AgentTask.project_id == project_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if not task.blackboard_snapshot:
        return {"status": "error", "message": "No snapshot available for this task"}
    if task.status != "completed":
        return {"status": "error", "message": "Only completed tasks can be re-run"}

    from app.agents.blackboard import Blackboard
    from app.agents.autonomy import AutonomyConfig

    try:
        snapshot = json.loads(task.blackboard_snapshot)
        autonomy = AutonomyConfig.from_dict(snapshot.get("autonomy_config", {}))
        blackboard = Blackboard.from_snapshot(snapshot)
    except Exception as e:
        return {"status": "error", "message": f"Failed to restore snapshot: {e}"}

    # Create a new task for the re-run
    new_task = AgentTask(
        id=str(uuid.uuid4()),
        project_id=project_id,
        task_type=task.task_type,
        target_desc=f"Re-run: {task.target_desc or task.task_type}",
        autonomy_config=json.dumps(autonomy.to_dict()),
        orchestrator_state="RUNNING",
        status="running",
    )
    db.add(new_task)
    db.commit()

    return {
        "status": "ok",
        "message": "New task created from snapshot",
        "new_task_id": new_task.id,
    }


class ChapterDiffQuery(BaseModel):
    chapter_id: str


@router.get("/tasks/{task_id}/chapter-diff")
async def chapter_diff(
    task_id: str,
    project_id: str,
    chapter_id: str = Query(""),
    db: Session = Depends(get_db),
):
    """Get chapter content diff between current state and snapshot before this task."""
    from app.models.chapter import Chapter
    from app.models.chapter_snapshot import ChapterSnapshot

    task = db.query(AgentTask).filter(AgentTask.id == task_id, AgentTask.project_id == project_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Find the snapshot taken before this task modified the chapter
    snapshots = (
        db.query(ChapterSnapshot)
        .filter(ChapterSnapshot.task_id == task_id)
        .all()
    )

    if not snapshots:
        return {"error": "No snapshot found for this task", "before_snippet": "", "after_snippet": "", "summary": "无快照"}

    result_snapshots = []
    for snap in snapshots:
        chapter = db.query(Chapter).filter(Chapter.id == snap.chapter_id).first()
        result_snapshots.append({
            "chapter_id": snap.chapter_id,
            "chapter_title": snap.title,
            "before_snippet": (snap.content or "")[:500],
            "after_snippet": (chapter.content if chapter else "")[:500],
            "summary": f"章节「{snap.title}」在任务执行前的内容",
        })

    if chapter_id:
        result_snapshots = [s for s in result_snapshots if s["chapter_id"] == chapter_id]

    return {
        "task_id": task_id,
        "changes": result_snapshots,
        "count": len(result_snapshots),
    }


@router.post("/tasks/{task_id}/restore-chapter")
async def restore_chapter(
    task_id: str,
    project_id: str,
    body: RollbackRequest,
    db: Session = Depends(get_db),
):
    """Restore chapter content to the state before this task modified it."""
    from app.models.chapter import Chapter
    from app.models.chapter_snapshot import ChapterSnapshot

    task = db.query(AgentTask).filter(AgentTask.id == task_id, AgentTask.project_id == project_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    snapshot = (
        db.query(ChapterSnapshot)
        .filter(ChapterSnapshot.task_id == task_id, ChapterSnapshot.chapter_id == body.chapter_id)
        .first()
    )
    if not snapshot:
        return {"status": "error", "message": "No snapshot found to restore from"}

    chapter = db.query(Chapter).filter(Chapter.id == body.chapter_id).first()
    if not chapter:
        return {"status": "error", "message": "Chapter not found"}

    chapter.content = snapshot.content
    chapter.title = snapshot.title
    db.commit()

    return {
        "status": "ok",
        "message": "Chapter restored to pre-task state",
        "chapter_id": body.chapter_id,
    }
