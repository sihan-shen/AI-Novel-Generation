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
from datetime import datetime, timedelta

_project_locks: dict[str, asyncio.Lock] = {}

def _get_project_lock(project_id: str) -> asyncio.Lock:
    if project_id not in _project_locks:
        _project_locks[project_id] = asyncio.Lock()
    return _project_locks[project_id]


def _get_active_task(db: Session, project_id: str):
    """Get the currently active (running or waiting_user) task for a project."""
    return db.query(AgentTask).filter(
        AgentTask.project_id == project_id,
        AgentTask.status.in_(["running", "waiting_user"]),
    ).order_by(AgentTask.updated_at.desc()).first()


async def _detect_intent(adapter, message: str) -> str:
    """Classify user intent as 'brainstorm', 'writing', or 'other'."""
    prompt = f"""用户消息: "{message}"

判断意图：
- "brainstorm": 创意帮助、灵感拓展、方案探索、设定讨论。
  隐含表达："还能怎么玩"、"卡住了"、"没思路"、"有什么推荐"、"给我几个方案"、"不知道怎么"、"不够精彩"
- "writing": 明确的写作/修改/生成请求。边界：即使用户表达困惑（"不知道怎么写第一章"），只要提到具体章节/写作动作，归类为 writing
- "other": 以上都不是

返回 JSON: {{"intent": "brainstorm|writing|other"}}"""

    try:
        response = await adapter.generate(
            [{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=50,
        )
        import json
        result = json.loads(response.content)
        return result.get("intent", "other")
    except Exception:
        return "other"


def _check_timeout(db: Session, task: AgentTask) -> bool:
    """Check if the active task has timed out (15 min since last message)."""
    from app.models.agent_message import AgentMessage
    last_msg = db.query(AgentMessage).filter(
        AgentMessage.task_id == task.id,
    ).order_by(AgentMessage.created_at.desc()).first()

    if last_msg and last_msg.created_at:
        elapsed = datetime.utcnow() - last_msg.created_at
        if elapsed > timedelta(minutes=15):
            task.status = "timeout"
            task.completed_at = datetime.utcnow()
            db.commit()
            return True
    return False


async def _handle_brainstorm_turn(
    db: Session,
    task: AgentTask,
    message: str,
    project_id: str,
    adapter,
) -> list[dict]:
    """Execute one turn of brainstorm: load history, run agent, persist response."""
    from app.agents.base import run_agent
    from app.agents.agents.brainstorm import build_brainstorm_config
    from app.agents.blackboard import Blackboard
    from app.agents.autonomy import AutonomyConfig

    # Check for commands
    if message.strip() in ("/done", "/end"):
        task.status = "completed"
        task.completed_at = datetime.utcnow()
        db.commit()
        return [{"type": "brainstorm_end", "message": "脑暴已结束", "pending_inspirations": task.task_metadata.get("pending_inspirations", [])}]

    if message.strip() in ("/cancel",):
        task.status = "cancelled"
        task.completed_at = datetime.utcnow()
        db.commit()
        return [{"type": "brainstorm_end", "message": "脑暴已取消"}]

    # Load recent message history (last 20 turns)
    from app.models.agent_message import AgentMessage
    recent_msgs = db.query(AgentMessage).filter(
        AgentMessage.task_id == task.id,
    ).order_by(AgentMessage.sequence).all()

    history = []
    for m in recent_msgs[-20:]:  # Last 20 messages
        history.append({"role": m.role, "content": m.content})

    # Build context with minimal project info + history
    from app.services.project_service import ProjectService
    project = ProjectService.get(db, project_id)
    context_lines = [f"项目: {project.title if project else project_id}"]
    if project and project.genre:
        context_lines.append(f"类型: {project.genre}")

    # Build agent config and run
    config = build_brainstorm_config(db=db, project_id=project_id, task_id=task.id)
    blackboard = Blackboard(
        project_id=project_id,
        task={"type": "brainstorm", "task_id": task.id},
        autonomy_config=AutonomyConfig(),
    )

    blackboard._settings_context = "\n".join(context_lines)  # Minimal context

    # Override get_context_for to include history
    original_get_context = blackboard.get_context_for
    def _brainstorm_context(agent_type: str) -> str:
        base = original_get_context(agent_type)
        if history:
            hist_text = "\n\n=== 当前脑暴对话 ===\n"
            for h in history[-20:]:
                role_label = "用户" if h["role"] == "user" else "顾问"
                hist_text += f"\n{role_label}: {h['content'][:500]}"
            base += hist_text
        return base
    blackboard.get_context_for = _brainstorm_context

    result = await run_agent(config, blackboard, adapter)

    # Handle handoff
    if result.status == "handoff":
        task.status = "completed"
        task.completed_at = datetime.utcnow()
        db.commit()
        return [{
            "type": "brainstorm_handoff",
            "summary": result.output,
            "user_message": message,
            "pending_inspirations": task.task_metadata.get("pending_inspirations", []),
        }]

    # Persist assistant response as AgentMessage
    import uuid
    seq = len(recent_msgs) + 1
    user_msg_obj = AgentMessage(
        id=str(uuid.uuid4()),
        task_id=task.id,
        role="user",
        content=message[:2000],
        message_type="user_message",
        sequence=seq,
    )
    db.add(user_msg_obj)

    seq += 1
    assistant_msg = AgentMessage(
        id=str(uuid.uuid4()),
        task_id=task.id,
        role="assistant",
        content=result.output[:2000],
        message_type="agent_output",
        sequence=seq,
    )
    db.add(assistant_msg)
    task.total_steps = seq
    if result.steps:
        task.total_tokens = (task.total_tokens or 0) + result.steps[0].token_usage.get("input_tokens", 0) + result.steps[0].token_usage.get("output_tokens", 0)
    task.updated_at = datetime.utcnow()
    db.commit()

    # Build SSE events
    events = [{"type": "brainstorm_response", "content": result.output, "sequence": seq}]

    # Include tool calls if any
    for step in result.steps:
        events.append({
            "type": "tool_call",
            "tool": step.tool_name,
            "args": step.tool_args,
            "sequence": seq,
        })

    # Check turn limit
    turn_count = task.task_metadata.get("turn_count", 0) + 1
    task.update_task_metadata(turn_count=turn_count)
    db.commit()
    if turn_count >= 100:
        task.status = "completed"
        task.completed_at = datetime.utcnow()
        db.commit()
        events.append({"type": "brainstorm_end", "message": "已达到最大轮数(100)，脑暴自动结束", "pending_inspirations": task.task_metadata.get("pending_inspirations", [])})

    return events


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
