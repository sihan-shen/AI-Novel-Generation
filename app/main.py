import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routers import (
    agent,
    chapters,
    config,
    ideas,
    outline_gen,
    outlines,
    projects,
    reviews,
    search,
    settings,
    styles,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(BASE_DIR.parent / "data", exist_ok=True)
    init_db()
    from app.database import engine
    from app.migrations import (
        m001_token_usage_to_ai_call,
        m002_add_agent_task_columns,
        m003_add_idea_updated_at,
    )
    m001_token_usage_to_ai_call.run(engine)
    m002_add_agent_task_columns.run(engine)
    m003_add_idea_updated_at.run(engine)
    _recover_agent_tasks()
    logger.info("Application startup complete")
    yield
    logger.info("Application shutdown")


app = FastAPI(title="AI Novel Generation Tool", lifespan=lifespan)

# CORS middleware — allow frontend dev servers
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).parent


@app.get("/")
async def root():
    """API root — the frontend UI is served by Next.js (localhost:3000 in dev)."""
    return {
        "app": "Novel Forge API",
        "version": "0.2.0",  # sync with pyproject.toml
        "docs": "/docs",
        "openapi": "/openapi.json",
        "frontend": "http://localhost:3000",
    }


# JSON API routers
app.include_router(projects.router)
app.include_router(outlines.router)
app.include_router(settings.router)
app.include_router(chapters.router)
app.include_router(styles.router)
app.include_router(reviews.router)
app.include_router(ideas.router)
app.include_router(config.router)

# Functional routers (SSE / agent / search / outline generation)
app.include_router(outline_gen.router)
app.include_router(search.router)
app.include_router(agent.router)


def _recover_agent_tasks():
    """Recover agent tasks that were interrupted by a restart.

    - running tasks with a valid mid-run snapshot and non-terminal state become
      ``waiting_user`` (resumable — user must explicitly click continue).
    - running tasks without a snapshot or in a terminal state become ``failed``.
    - waiting_user tasks are left untouched so a server restart does not cancel
      a user-paused conversation.
    """
    from app.database import get_db_context
    from app.models.agent_task import AgentTask

    with get_db_context() as db:
        running_tasks = db.query(AgentTask).filter(
            AgentTask.status.in_(["running", "waiting_user"])
        ).all()
        for task in running_tasks:
            try:
                if task.status == "waiting_user":
                    logger.warning(
                        "Recovery: task %s kept waiting_user (user-paused)", task.id
                    )
                    continue

                snapshot_json = task.blackboard_snapshot
                can_resume = False
                if snapshot_json:
                    snapshot = json.loads(snapshot_json)
                    state = snapshot.get("orchestrator_state", task.orchestrator_state)
                    if state not in ("DONE", "CANCELLED", "IDLE"):
                        can_resume = True

                if can_resume:
                    task.status = "waiting_user"
                    logger.warning(
                        "Recovery: task %s moved to waiting_user (resumable)", task.id
                    )
                else:
                    task.status = "failed"
                    task.orchestrator_state = "CANCELLED"
                    logger.warning(
                        "Recovery: task %s marked failed (no resumable snapshot)", task.id
                    )
                    import uuid

                    from app.models.agent_message import AgentMessage
                    msg = AgentMessage(
                        id=str(uuid.uuid4()),
                        task_id=task.id,
                        role="system",
                        content=f"Task auto-cancelled on server restart. Previous state: {task.orchestrator_state}",  # noqa: E501
                        message_type="error",
                        sequence=9999,
                    )
                    db.add(msg)
                db.commit()
            except Exception as exc:
                logger.warning(
                    "Recovery: task %s skipped due to error: %s", task.id, exc
                )
                db.rollback()


def _get_server_config():
    """Read host/port from DB config, falling back to env defaults."""
    try:
        from app.database import get_db_context
        from app.services.config_service import ConfigService
        with get_db_context() as db:
            cfg = ConfigService.get_all(db)
            return cfg.get("host", "0.0.0.0"), int(cfg.get("port", 8000))
    except Exception:
        return "0.0.0.0", 8000


def start():
    """Entry point for `novel-forge` CLI command."""
    import uvicorn
    host, port = _get_server_config()
    uvicorn.run("app.main:app", host=host, port=port)


if __name__ == "__main__":
    import uvicorn
    host, port = _get_server_config()
    uvicorn.run("app.main:app", host=host, port=port, reload=True)
