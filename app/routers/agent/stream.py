"""SSE streaming helpers: resume event replay."""

from __future__ import annotations

import json
import logging
from typing import AsyncGenerator

from sqlalchemy.orm import Session

from app.models.agent_message import AgentMessage
from app.models.agent_task import AgentTask

logger = logging.getLogger(__name__)


async def resume_events(
    db: Session, project_id: str, resume_from: int
) -> AsyncGenerator[str, None]:
    """Replay past agent messages from the given sequence number for SSE reconnect."""
    try:
        task = (
            db.query(AgentTask)
            .filter(
                AgentTask.project_id == project_id,
                AgentTask.status.in_(["running", "waiting_user"]),
            )
            .order_by(AgentTask.created_at.desc())
            .first()
        )
    except Exception:
        logger.exception("Failed to query active task for resume, project %s", project_id)
        raise
    if task:
        try:
            old_msgs = (
                db.query(AgentMessage)
                .filter(
                    AgentMessage.task_id == task.id,
                    AgentMessage.sequence >= resume_from,
                )
                .order_by(AgentMessage.sequence)
                .all()
            )
        except Exception:
            logger.exception("Failed to query old messages for resume, task %s", task.id)
            raise
        for m in old_msgs:
            try:
                event_data = (
                    json.loads(str(m.msg_metadata or "{}")) if m.msg_metadata else {}
                )
                yield (
                    f"event: {m.message_type}\n"
                    f"data: {json.dumps({'sequence': m.sequence, **event_data}, ensure_ascii=False)}\n\n"  # noqa: E501
                )
            except Exception:
                logger.exception("Failed to serialize resume event for message %s", m.id)
                raise
        yield (
            f"event: reconnect\n"
            f'data: {{"status": "reconnected", "task_id": "{task.id}"}}\n\n'  # noqa: E501
        )
    else:
        yield 'event: reconnect\ndata: {"status": "no_active_task"}\n\n'
