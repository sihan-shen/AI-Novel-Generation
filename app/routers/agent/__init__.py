"""Agent router package — SSE streaming, task management, brainstorm, orchestration."""

from app.routers.agent.shared import router
from app.routers.agent import routes  # noqa: F401 — side-effect: register route handlers on router

__all__ = ["router"]
