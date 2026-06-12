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

        adapter = get_adapter(db)
        lock = _get_project_lock(project_id)

        # ---- Check for existing active task ----
        async with lock:
            active_task = _get_active_task(db, project_id)

            if active_task and active_task.task_type == "brainstorm":
                # Check timeout
                if _check_timeout(db, active_task):
                    yield f"event: brainstorm_end\ndata: {json.dumps({'message': '脑暴已超时', 'timeout': True}, ensure_ascii=False)}\n\n"
                    return

                # Handle brainstorm turn
                events = await _handle_brainstorm_turn(
                    db, active_task, body.message, project_id, adapter
                )

                # Handle handoff from brainstorm
                handoff_event = next((e for e in events if e["type"] == "brainstorm_handoff"), None)
                if handoff_event:
                    yield f"event: brainstorm_end\ndata: {json.dumps({'message': '切换到写作模式', 'handoff': True}, ensure_ascii=False)}\n\n"
                    yield f"event: orchestrator_thought\ndata: {json.dumps({'text': '脑暴已完成，请重新发送写作请求'}, ensure_ascii=False)}\n\n"
                    return

                # Emit brainstorm events
                seq = 0
                for event in events:
                    seq += 1
                    yield f"event: {event['type']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
                return

            # ---- No active task: detect intent ----
            if active_task is None:
                # Check for explicit /brainstorm command
                if body.message.strip().startswith("/brainstorm"):
                    intent = "brainstorm"
                else:
                    intent = await _detect_intent(adapter, body.message)

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
                    db.commit()

                    yield f"event: agent_start\ndata: {json.dumps({'agent': 'brainstorm', 'task_id': task_obj.id}, ensure_ascii=False)}\n\n"

                    events = await _handle_brainstorm_turn(
                        db, task_obj, body.message, project_id, adapter
                    )
                    seq = 0
                    for event in events:
                        seq += 1
                        yield f"event: {event['type']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
                    return

        # ---- Normal orchestrator flow (original code, outside the async with lock) ----
        from app.agents.blackboard import Blackboard
        from app.agents.autonomy import AutonomyConfig
        from app.agents.orchestrator import Orchestrator

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

                    if seq % 10 == 1:
                        task_obj.total_steps = seq
                        db.commit()
                except asyncio.TimeoutError:
                    if orch_task.done():
                        break
        finally:
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
async def list_tasks(project_id: str, db: Session = Depends(get_db)):
    from app.models.agent_task import AgentTask
    tasks = db.query(AgentTask).filter(AgentTask.project_id == project_id).order_by(AgentTask.created_at.desc()).limit(20).all()
    return {"tasks": [{"id": t.id, "task_type": t.task_type, "status": t.status, "total_steps": t.total_steps, "total_tokens": t.total_tokens, "created_at": t.created_at.isoformat() if t.created_at else None, "completed_at": t.completed_at.isoformat() if t.completed_at else None} for t in tasks]}


class ConfirmInspirationsRequest(BaseModel):
    inspiration_ids: list[str]


@router.post("/inspirations/confirm")
async def confirm_inspirations(
    project_id: str,
    body: ConfirmInspirationsRequest,
    db: Session = Depends(get_db),
):
    """Confirm and save selected inspirations from a completed brainstorm session."""
    from app.services.idea_service import IdeaService
    from app.services.setting_service import SettingService
    from app.services.outline_service import OutlineService
    from app.schemas.setting import SettingCreate
    from app.schemas.outline import OutlineCreate

    # Find the most recent completed brainstorm task
    task = db.query(AgentTask).filter(
        AgentTask.project_id == project_id,
        AgentTask.task_type == "brainstorm",
        AgentTask.status == "completed",
    ).order_by(AgentTask.updated_at.desc()).first()

    if not task:
        return {"status": "error", "message": "No completed brainstorm session found"}

    pending = task.task_metadata.get("pending_inspirations", [])
    saved_count = 0

    for insp in pending:
        if insp["id"] not in body.inspiration_ids:
            continue
        if insp["type"] == "idea":
            IdeaService.create(
                db, project_id=project_id,
                title=insp.get("title", "灵感"),
                content=insp.get("content", ""),
                source="brainstorm",
            )
            saved_count += 1
        elif insp["type"] == "setting":
            SettingService.create(db, SettingCreate(
                project_id=project_id,
                category=insp.get("category", "自定义"),
                name=insp.get("title", "未命名"),
                summary=insp.get("content", "")[:500],
                content=insp.get("content", ""),
                weight=5,
            ))
            saved_count += 1
        elif insp["type"] == "outline":
            OutlineService.create(db, OutlineCreate(
                project_id=project_id,
                level=2,
                title=insp.get("title", "未命名"),
                summary=insp.get("content", "")[:500],
            ))
            saved_count += 1

    # Remove confirmed items from pending
    remaining = [i for i in pending if i["id"] not in body.inspiration_ids]
    task.update_task_metadata(pending_inspirations=remaining)
    db.commit()

    return {"status": "ok", "saved_count": saved_count}
