"""Orchestrator lifecycle management."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.agents.autonomy import AutonomyConfig
from app.agents.blackboard import Blackboard
from app.agents.orchestrator import Orchestrator
from app.models.agent_message import AgentMessage
from app.models.agent_task import AgentTask
from app.routers.agent.models import ChatRequest
from app.routers.agent.shared import _pending_confirms, _running_orchestrators
from app.database import get_db_context

logger = logging.getLogger(__name__)


def cleanup_orchestrator(
    task_obj: AgentTask, blackboard, seq: int, orch_db: Session | None, db: Session
):
    """Persist final orchestrator state and close the orchestrator DB session."""
    _running_orchestrators.pop(str(task_obj.id), None)
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


async def _run_orchestrator_flow(
    db: Session, adapter, body: ChatRequest, project_id: str
):
    """Create write_chapter orchestrator, stream events, persist messages, cleanup."""
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
    blackboard = None
    try:
        with get_db_context() as orch_db:
            blackboard = Blackboard(
                project_id=project_id, task=task_def, autonomy_config=autonomy
            )
            orch = Orchestrator(
                db=orch_db, blackboard=blackboard, adapter=adapter, task_id=str(task_obj.id)
            )
            _running_orchestrators[str(task_obj.id)] = orch
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
        cleanup_orchestrator(task_obj, blackboard, seq, orch_db, db)

    yield "event: done\ndata: {}\n\n"
