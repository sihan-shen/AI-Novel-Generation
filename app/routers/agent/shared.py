"""Shared module-level state and helpers for agent routes."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter
from sqlalchemy.orm import Session

from app.models.agent_message import AgentMessage
from app.models.agent_task import AgentTask

logger = logging.getLogger(__name__)


class AgentRouteError(Exception):
    """Base exception for agent route errors.

    Attributes:
        recoverable: Whether the error is recoverable (True) or fatal (False).
    """

    def __init__(self, message: str, *, recoverable: bool = True):
        super().__init__(message)
        self.recoverable = recoverable


class DatabaseQueryError(AgentRouteError):
    """Raised when a DB query fails unexpectedly."""


class OrchestrationError(AgentRouteError):
    """Raised when the orchestrator encounters a fatal error."""

    def __init__(self, message: str, *, task_id: str | None = None):
        super().__init__(message, recoverable=False)
        self.task_id = task_id


# Module-level state
_project_locks: dict[str, asyncio.Lock] = {}
_pending_confirms: dict[str, asyncio.Event] = {}
_confirm_outcomes: dict[str, dict] = {}
_running_orchestrators: dict[str, object] = {}  # Orchestrator instances


def get_project_lock(project_id: str) -> asyncio.Lock:
    if project_id not in _project_locks:
        _project_locks[project_id] = asyncio.Lock()
    return _project_locks[project_id]


def get_active_task(db: Session, project_id: str) -> AgentTask | None:
    """Get the currently active (running or waiting_user) task for a project."""
    return (
        db.query(AgentTask)
        .filter(
            AgentTask.project_id == project_id,
            AgentTask.status.in_(["running", "waiting_user"]),
        )
        .order_by(AgentTask.updated_at.desc())
        .first()
    )


def check_timeout(db: Session, task: AgentTask) -> bool:
    """Check if the active task has timed out (15 min since last message).
    Mutates task status to 'timeout' and commits the change.
    Returns True if timed out.
    """
    last_msg = (
        db.query(AgentMessage)
        .filter(AgentMessage.task_id == task.id)
        .order_by(AgentMessage.created_at.desc())
        .first()
    )
    if last_msg and last_msg.created_at:
        msg_time = last_msg.created_at
        if msg_time.tzinfo is None:
            msg_time = msg_time.replace(tzinfo=UTC)
        elapsed = datetime.now(UTC) - msg_time
        if elapsed > timedelta(minutes=15):
            task.status = "timeout"  # type: ignore[assignment]
            task.completed_at = datetime.now(UTC)  # type: ignore[assignment]
            db.commit()
            return True
    return False


# Router — routes are registered in agent.py (Tasks 3-5 will move them)
router = APIRouter(prefix="/api/project/{project_id}/agent", tags=["agent"])
