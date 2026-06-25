"""Brainstorm flow: intent detection, turn execution, inspiration confirmation."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.agents.agents.brainstorm import build_brainstorm_config
from app.agents.autonomy import AutonomyConfig
from app.agents.base import run_agent
from app.agents.blackboard import Blackboard
from app.models.agent_message import AgentMessage
from app.models.agent_task import AgentTask
from app.routers.agent.models import ConfirmInspirationsRequest
from app.routers.agent.shared import check_timeout
from app.schemas.outline import OutlineCreate
from app.schemas.setting import SettingCreate
from app.schemas.response import APIResponse
from app.services.idea_service import IdeaService
from app.services.outline_service import OutlineService
from app.services.setting_service import SettingService

logger = logging.getLogger(__name__)


async def detect_intent(adapter, message: str) -> str:
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
        result = json.loads(response.content)
        return result.get("intent", "other")
    except Exception:
        logger.warning("Intent detection failed, defaulting to 'other'")
        return "other"


async def handle_brainstorm_turn(
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


async def handle_brainstorm_flow(
    db: Session, adapter, task: AgentTask, message: str, project_id: str
):
    """Handle existing brainstorm task: timeout check, turn execution, SSE event emission."""
    if check_timeout(db, task):
        yield f"event: brainstorm_end\ndata: {json.dumps({'message': '脑暴已超时', 'timeout': True}, ensure_ascii=False)}\n\n"  # noqa: E501
        return

    events = await handle_brainstorm_turn(db, task, message, project_id, adapter)

    handoff_event = next((e for e in events if e["type"] == "brainstorm_handoff"), None)
    if handoff_event:
        yield f"event: brainstorm_end\ndata: {json.dumps({'message': '切换到写作模式', 'handoff': True}, ensure_ascii=False)}\n\n"  # noqa: E501
        yield f"event: orchestrator_thought\ndata: {json.dumps({'text': '脑暴已完成，请重新发送写作请求'}, ensure_ascii=False)}\n\n"  # noqa: E501
        return

    for event in events:
        yield f"event: {event['type']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"  # noqa: E501


async def confirm_inspirations_handler(
    project_id: str,
    body: ConfirmInspirationsRequest,
    db: Session,
) -> APIResponse[dict]:
    """Confirm and save selected inspirations from a completed brainstorm session."""
    task = (
        db.query(AgentTask)
        .filter(
            AgentTask.project_id == project_id,
            AgentTask.task_type == "brainstorm",
            AgentTask.status == "completed",
        )
        .order_by(AgentTask.updated_at.desc())
        .first()
    )

    if not task:
        return APIResponse(
            data={"status": "error", "message": "No completed brainstorm session found"}
        )

    pending = task.task_metadata.get("pending_inspirations", [])
    saved_count = 0

    for insp in pending:
        if insp["id"] not in body.inspiration_ids:
            continue
        if insp["type"] == "idea":
            IdeaService.create(
                db,
                project_id=project_id,
                title=insp.get("title", "灵感"),
                content=insp.get("content", ""),
                source="brainstorm",
            )
            saved_count += 1
        elif insp["type"] == "setting":
            SettingService.create(
                db,
                SettingCreate(
                    project_id=project_id,
                    category=insp.get("category", "自定义"),
                    name=insp.get("title", "未命名"),
                    summary=insp.get("content", "")[:500],
                    content=insp.get("content", ""),
                    weight=5,
                ),
            )
            saved_count += 1
        elif insp["type"] == "outline":
            OutlineService.create(
                db,
                OutlineCreate(
                    project_id=project_id,
                    level=2,
                    title=insp.get("title", "未命名"),
                    summary=insp.get("content", "")[:500],
                ),
            )
            saved_count += 1

    remaining = [i for i in pending if i["id"] not in body.inspiration_ids]
    task.update_task_metadata(pending_inspirations=remaining)
    db.commit()

    return APIResponse(data={"status": "ok", "saved_count": saved_count})
