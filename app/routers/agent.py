"""Agent router — SSE streaming + task API."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.orchestrator import Orchestrator
from app.database import SessionLocal, get_db
from app.llm.adapter import get_adapter
from app.models.agent_message import AgentMessage
from app.models.agent_task import AgentTask
from app.schemas.response import APIResponse

_project_locks: dict[str, asyncio.Lock] = {}
_pending_confirms: dict[str, asyncio.Event] = {}
_confirm_outcomes: dict[str, dict] = {}
_running_orchestrators: dict[str, Orchestrator] = {}  # noqa: F821

logger = logging.getLogger(__name__)


def _get_project_lock(project_id: str) -> asyncio.Lock:
    if project_id not in _project_locks:
        _project_locks[project_id] = asyncio.Lock()
    return _project_locks[project_id]


def _get_active_task(db: Session, project_id: str):
    """Get the currently active (running or waiting_user) task for a project."""
    try:
        return db.query(AgentTask).filter(
            AgentTask.project_id == project_id,
            AgentTask.status.in_(["running", "waiting_user"]),
        ).order_by(AgentTask.updated_at.desc()).first()
    except Exception:
        logger.exception("Failed to query active task for project %s", project_id)
        raise


async def _detect_intent(adapter, message: str) -> str:
    """Classify user intent as 'brainstorm', 'writing', or 'other'."""
    prompt = f"""用户消息: "{message}"

判断意图：
- "brainstorm": 创意帮助、灵感拓展、方案探索、设定讨论。
  隐含表达："还能怎么玩"、"卡住了"、"没思路"、"有什么推荐"、"给我几个方案"、"不知道怎么"、"不够精彩"
- "writing": 明确的写作/修改/生成请求。边界：即使用户表达困惑（"不知道怎么写第一章"），
  只要提到具体章节/写作动作，归类为 writing
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
    try:
        last_msg = db.query(AgentMessage).filter(
            AgentMessage.task_id == task.id,
        ).order_by(AgentMessage.created_at.desc()).first()
    except Exception:
        logger.exception("Failed to query last message for timeout check, task_id=%s", task.id)
        raise

    if last_msg and last_msg.created_at:
        elapsed = datetime.now(UTC) - last_msg.created_at
        if elapsed > timedelta(minutes=15):
            task.status = "timeout"  # type: ignore[assignment]
            task.completed_at = datetime.now(UTC)  # type: ignore[assignment]
            try:
                db.commit()
            except Exception:
                logger.exception("Failed to commit timeout status for task %s", task.id)
                db.rollback()
                raise
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
    from app.agents.agents.brainstorm import build_brainstorm_config
    from app.agents.autonomy import AutonomyConfig
    from app.agents.base import run_agent
    from app.agents.blackboard import Blackboard

    # Check for commands
    if message.strip() in ("/done", "/end"):
        task.status = "completed"  # type: ignore[assignment]
        task.completed_at = datetime.now(UTC)  # type: ignore[assignment]
        try:
            db.commit()
        except Exception:
            logger.exception("Failed to commit /done status for task %s", task.id)
            db.rollback()
            raise
        return [{"type": "brainstorm_end", "message": "脑暴已结束", "pending_inspirations": task.task_metadata.get("pending_inspirations", [])}]  # noqa: E501

    if message.strip() in ("/cancel",):
        task.status = "cancelled"  # type: ignore[assignment]
        task.completed_at = datetime.now(UTC)  # type: ignore[assignment]
        try:
            db.commit()
        except Exception:
            logger.exception("Failed to commit /cancel status for task %s", task.id)
            db.rollback()
            raise
        return [{"type": "brainstorm_end", "message": "脑暴已取消"}]

    # Load recent message history (last 20 turns)
    from app.models.agent_message import AgentMessage
    try:
        recent_msgs = db.query(AgentMessage).filter(
            AgentMessage.task_id == task.id,
        ).order_by(AgentMessage.sequence).all()
    except Exception:
        logger.exception("Failed to query recent messages for task %s", task.id)
        raise

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
    config = build_brainstorm_config(db=db, project_id=project_id, task_id=task.id)  # type: ignore[arg-type]
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
    blackboard.get_context_for = _brainstorm_context  # type: ignore[method-assign]

    try:
        result = await run_agent(config, blackboard, adapter, db=db, agent_type="brainstorm")
    except Exception:
        logger.exception("run_agent failed for brainstorm task %s", task.id)
        raise

    # Handle handoff
    if result.status == "handoff":
        task.status = "completed"  # type: ignore[assignment]
        task.completed_at = datetime.now(UTC)  # type: ignore[assignment]
        try:
            db.commit()
        except Exception:
            logger.exception("Failed to commit handoff status for task %s", task.id)
            db.rollback()
            raise
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
    task.total_steps = seq  # type: ignore[assignment]
    if result.steps:
        task.total_tokens = (task.total_tokens or 0) + result.steps[0].token_usage.get("input_tokens", 0) + result.steps[0].token_usage.get("output_tokens", 0)  # noqa: E501
    task.updated_at = datetime.now(UTC)  # type: ignore[assignment]
    try:
        db.commit()
    except Exception:
        logger.exception("Failed to persist brainstorm messages for task %s", task.id)
        db.rollback()
        raise

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
    try:
        db.commit()
    except Exception:
        logger.exception("Failed to update turn count for task %s", task.id)
        db.rollback()
        raise
    if turn_count >= 100:
        task.status = "completed"  # type: ignore[assignment]
        task.completed_at = datetime.now(UTC)  # type: ignore[assignment]
        try:
            db.commit()
        except Exception:
            logger.exception("Failed to commit turn-limit completion for task %s", task.id)
            db.rollback()
            raise
        events.append({"type": "brainstorm_end", "message": "已达到最大轮数(100)，脑暴自动结束", "pending_inspirations": task.task_metadata.get("pending_inspirations", [])})  # noqa: E501

    return events


async def _resume_events(db: Session, project_id: str, resume_from: int):
    """Replay past agent messages from the given sequence number for SSE reconnect."""
    try:
        task = db.query(AgentTask).filter(
            AgentTask.project_id == project_id,
            AgentTask.status.in_(["running", "waiting_user"]),
        ).order_by(AgentTask.created_at.desc()).first()
    except Exception:
        logger.exception("Failed to query active task for resume, project %s", project_id)
        raise
    if task:
        try:
            old_msgs = db.query(AgentMessage).filter(
                AgentMessage.task_id == task.id,
                AgentMessage.sequence >= resume_from,
            ).order_by(AgentMessage.sequence).all()
        except Exception:
            logger.exception("Failed to query old messages for resume, task %s", task.id)
            raise
        for m in old_msgs:
            try:
                event_data = json.loads(m.msg_metadata or "{}") if m.msg_metadata else {}
                yield f"event: {m.message_type}\ndata: {json.dumps({'sequence': m.sequence, **event_data}, ensure_ascii=False)}\n\n"  # noqa: E501
            except Exception:
                logger.exception("Failed to serialize resume event for message %s", m.id)
                raise
        yield f"event: reconnect\ndata: {{\"status\": \"reconnected\", \"task_id\": \"{task.id}\"}}\n\n"  # noqa: E501
    else:
        yield "event: reconnect\ndata: {\"status\": \"no_active_task\"}\n\n"


async def _handle_brainstorm_flow(
    db: Session, adapter, task: AgentTask, message: str, project_id: str
):
    """Handle existing brainstorm task: timeout check, turn execution, SSE event emission."""
    if _check_timeout(db, task):
        yield f"event: brainstorm_end\ndata: {json.dumps({'message': '脑暴已超时', 'timeout': True}, ensure_ascii=False)}\n\n"  # noqa: E501
        return

    events = await _handle_brainstorm_turn(db, task, message, project_id, adapter)

    handoff_event = next((e for e in events if e["type"] == "brainstorm_handoff"), None)
    if handoff_event:
        yield f"event: brainstorm_end\ndata: {json.dumps({'message': '切换到写作模式', 'handoff': True}, ensure_ascii=False)}\n\n"  # noqa: E501
        yield f"event: orchestrator_thought\ndata: {json.dumps({'text': '脑暴已完成，请重新发送写作请求'}, ensure_ascii=False)}\n\n"  # noqa: E501
        return

    for event in events:
        yield f"event: {event['type']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"  # noqa: E501


def _cleanup_orchestrator(
    task_obj: AgentTask, blackboard, seq: int, orch_db: Session | None, db: Session
):
    """Persist final orchestrator state and close the orchestrator DB session."""
    _running_orchestrators.pop(task_obj.id, None)
    if blackboard is not None:
        final_state = blackboard.orchestrator_state
        task_obj.orchestrator_state = final_state  # type: ignore[assignment]
        task_obj.total_steps = seq  # type: ignore[assignment]
        task_obj.total_tokens = blackboard.cumulative_tokens  # type: ignore[assignment]
        if final_state in ("DONE", "CANCELLED", "IDLE"):
            task_obj.status = "completed" if final_state == "DONE" else "cancelled"  # type: ignore[assignment]
            task_obj.completed_at = datetime.now(UTC)  # type: ignore[assignment]
        elif final_state == "WAITING_USER":
            task_obj.status = "waiting_user"  # type: ignore[assignment]
        with contextlib.suppress(Exception):
            task_obj.blackboard_snapshot = json.dumps(  # type: ignore[assignment]
                blackboard.to_snapshot(), ensure_ascii=False
            )
    try:
        db.commit()
    except Exception:
        logger.exception("Failed to commit cleanup state for task %s", task_obj.id)
        with contextlib.suppress(Exception):
            db.rollback()
    if orch_db is not None:
        orch_db.close()


async def _run_orchestrator_flow(
    db: Session, adapter, body: ChatRequest, project_id: str
):
    """Create write_chapter orchestrator, stream events, persist messages, cleanup."""
    from app.agents.autonomy import AutonomyConfig
    from app.agents.blackboard import Blackboard
    from app.agents.orchestrator import Orchestrator

    autonomy = AutonomyConfig()
    task_def = {
        "type": "write_chapter",
        "chapter_outline_id": body.chapter_outline_id,
        "target_words": body.target_words,
    }
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
    try:
        db.commit()
    except Exception:
        logger.exception("Failed to create orchestrator task for project %s", project_id)
        db.rollback()
        raise

    seq = 0
    orch_db = None
    blackboard = None
    try:
        orch_db = SessionLocal()
        blackboard = Blackboard(
            project_id=project_id, task=task_def, autonomy_config=autonomy
        )
        orch = Orchestrator(
            db=orch_db, blackboard=blackboard, adapter=adapter, task_id=task_obj.id
        )
        _running_orchestrators[task_obj.id] = orch
        orch_task = asyncio.create_task(orch.run())

        while not orch_task.done() or not blackboard.events.empty():
            try:
                event = await asyncio.wait_for(blackboard.events.get(), timeout=0.5)
                if event.get("type") == "confirm_request":
                    event_id = event.get("id")
                    if event_id and event_id in blackboard._confirm_events:
                        _pending_confirms[event_id] = blackboard._confirm_events[event_id]
                seq += 1
                event["sequence"] = seq
                try:
                    event_json = json.dumps(event, ensure_ascii=False)
                except Exception:
                    logger.exception(
                        "Failed to serialize orchestration event for task %s",
                        task_obj.id,
                    )
                    raise
                yield f"event: {event['type']}\ndata: {event_json}\n\n"  # noqa: E501

                content = event.get("text", event.get("summary", event.get("tool", "")))
                try:
                    msg_metadata_str = json.dumps(event, ensure_ascii=False)
                except Exception:
                    logger.exception("Failed to serialize msg_metadata for task %s", task_obj.id)
                    raise
                msg = AgentMessage(
                    id=str(uuid.uuid4()),
                    task_id=task_obj.id,
                    role="user" if event["type"] in ("user_message", "confirm_response") else "assistant",  # noqa: E501
                    content=str(content)[:2000],
                    message_type=event["type"],
                    msg_metadata=msg_metadata_str,
                    sequence=seq,
                )
                db.add(msg)
                try:
                    db.commit()
                except Exception:
                    logger.exception(
                        "Failed to persist orchestration event for task %s",
                        task_obj.id,
                    )
                    db.rollback()
                    raise

                if seq % 10 == 1:
                    task_obj.total_steps = seq  # type: ignore[assignment]
                    try:
                        db.commit()
                    except Exception:
                        logger.exception("Failed to update step count for task %s", task_obj.id)
                        db.rollback()
                        raise

                if seq % 5 == 0:
                    try:
                        task_obj.blackboard_snapshot = json.dumps(  # type: ignore[assignment]
                            blackboard.to_snapshot(), ensure_ascii=False
                        )
                        db.commit()
                    except Exception:
                        pass
            except TimeoutError:
                if orch_task.done():
                    orch_task.result()
                    break
    finally:
        _cleanup_orchestrator(task_obj, blackboard, seq, orch_db, db)

    yield "event: done\ndata: {}\n\n"


router = APIRouter(prefix="/api/project/{project_id}/agent", tags=["agent"])
class ChatRequest(BaseModel):
    message: str
    chapter_outline_id: str | None = None
    target_words: int = 3000


class ConfirmRequest(BaseModel):
    confirm_id: str
    action: str  # 'approve' | 'reject' | 'modify'
    modification: str | None = None


class CancelRequest(BaseModel):
    confirm_id: str | None = None
    task_id: str | None = None


@router.post("/chat/stream")
async def chat_stream(
    project_id: str,
    body: ChatRequest,
    resume_from: int = Query(0, description="Sequence number to resume from"),
    db: Session = Depends(get_db),
):
    async def event_stream():
        if resume_from > 0:
            async for event in _resume_events(db, project_id, resume_from):
                yield event
            return

        adapter = get_adapter(db)
        lock = _get_project_lock(project_id)

        async with lock:
            active_task = _get_active_task(db, project_id)

            if active_task and active_task.task_type == "brainstorm":
                async for event in _handle_brainstorm_flow(
                    db, adapter, active_task, body.message, project_id
                ):
                    yield event
                return

            if active_task is None:
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

                    async for event in _handle_brainstorm_flow(
                        db, adapter, task_obj, body.message, project_id
                    ):
                        yield event
                    return

        async for event in _run_orchestrator_flow(db, adapter, body, project_id):
            yield event

    return StreamingResponse(
        event_stream(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},  # noqa: E501
    )


@router.post("/chat/confirm", response_model=APIResponse[dict])
async def confirm_action(
    project_id: str,
    body: ConfirmRequest,
    db: Session = Depends(get_db),
):
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
    return APIResponse(data={"status": "ok", "message": f"Action '{body.action}' applied"})


@router.post("/chat/cancel", response_model=APIResponse[dict])
async def cancel_chat(
    project_id: str,
    body: CancelRequest | None = None,
    db: Session = Depends(get_db),
):
    """Request cancellation of the currently running orchestrator for a project."""
    active_task = _get_active_task(db, project_id)
    if active_task is None:
        return APIResponse(data={"status": "ok", "message": "No active task"})

    orch = _running_orchestrators.get(active_task.id)
    if orch is None:
        return APIResponse(data={"status": "ok", "message": "No active task"})

    orch.cancel()
    return APIResponse(data={"status": "ok", "message": "Cancellation requested"})


@router.get("/pending-actions", response_model=APIResponse[dict])
async def pending_actions(project_id: str, db: Session = Depends(get_db)):
    try:
        task = db.query(AgentTask).filter(
            AgentTask.project_id == project_id,
            AgentTask.status == "waiting_user",
        ).first()
    except Exception:
        logger.exception("Failed to query waiting task for project %s", project_id)
        raise
    actions = []
    if task:
        try:
            pending_msgs = db.query(AgentMessage).filter(
                AgentMessage.task_id == task.id,
                AgentMessage.message_type == "confirm_request",
            ).all()
        except Exception:
            logger.exception("Failed to query pending messages for task %s", task.id)
            raise
        actions = [{"id": m.id, "summary": m.content[:200]} for m in pending_msgs]
    return APIResponse(data={
        "has_pending": bool(task) or bool(_pending_confirms),
        "task_id": task.id if task else None,
        "actions": actions,
        "confirm_ids": list(_pending_confirms.keys()),
    })


@router.get("/tasks", response_model=APIResponse[dict])
async def list_tasks(project_id: str, db: Session = Depends(get_db)):
    from app.models.agent_task import AgentTask
    tasks = db.query(AgentTask).filter(AgentTask.project_id == project_id).order_by(AgentTask.created_at.desc()).limit(20).all()  # noqa: E501
    return APIResponse(data={"tasks": [{"id": t.id, "task_type": t.task_type, "status": t.status, "total_steps": t.total_steps, "total_tokens": t.total_tokens, "created_at": t.created_at.isoformat() if t.created_at else None, "completed_at": t.completed_at.isoformat() if t.completed_at else None} for t in tasks]})  # noqa: E501


class ConfirmInspirationsRequest(BaseModel):
    inspiration_ids: list[str]


@router.post("/inspirations/confirm", response_model=APIResponse[dict])
async def confirm_inspirations(
    project_id: str,
    body: ConfirmInspirationsRequest,
    db: Session = Depends(get_db),
):
    """Confirm and save selected inspirations from a completed brainstorm session."""
    from app.schemas.outline import OutlineCreate
    from app.schemas.setting import SettingCreate
    from app.services.idea_service import IdeaService
    from app.services.outline_service import OutlineService
    from app.services.setting_service import SettingService

    # Find the most recent completed brainstorm task
    try:
        task = db.query(AgentTask).filter(
            AgentTask.project_id == project_id,
            AgentTask.task_type == "brainstorm",
            AgentTask.status == "completed",
        ).order_by(AgentTask.updated_at.desc()).first()
    except Exception:
        logger.exception("Failed to query completed brainstorm task for project %s", project_id)
        raise

    if not task:
        return APIResponse(data={"status": "error", "message": "No completed brainstorm session found"})  # noqa: E501

    pending = task.task_metadata.get("pending_inspirations", [])
    saved_count = 0

    for insp in pending:
        if insp["id"] not in body.inspiration_ids:
            continue
        if insp["type"] == "idea":
            try:
                IdeaService.create(
                    db, project_id=project_id,
                    title=insp.get("title", "灵感"),
                    content=insp.get("content", ""),
                    source="brainstorm",
                )
            except Exception:
                logger.exception("Failed to save idea inspiration %s", insp.get("id"))
                db.rollback()
                raise
            saved_count += 1
        elif insp["type"] == "setting":
            try:
                SettingService.create(db, SettingCreate(
                    project_id=project_id,
                    category=insp.get("category", "自定义"),
                    name=insp.get("title", "未命名"),
                    summary=insp.get("content", "")[:500],
                    content=insp.get("content", ""),
                    weight=5,
                ))
            except Exception:
                logger.exception("Failed to save setting inspiration %s", insp.get("id"))
                db.rollback()
                raise
            saved_count += 1
        elif insp["type"] == "outline":
            try:
                OutlineService.create(db, OutlineCreate(
                    project_id=project_id,
                    level=2,
                    title=insp.get("title", "未命名"),
                    summary=insp.get("content", "")[:500],
                ))
            except Exception:
                logger.exception("Failed to save outline inspiration %s", insp.get("id"))
                db.rollback()
                raise
            saved_count += 1

    # Remove confirmed items from pending
    remaining = [i for i in pending if i["id"] not in body.inspiration_ids]
    task.update_task_metadata(pending_inspirations=remaining)
    try:
        db.commit()
    except Exception:
        logger.exception("Failed to commit inspiration confirmations for project %s", project_id)
        db.rollback()
        raise

    return APIResponse(data={"status": "ok", "saved_count": saved_count})
