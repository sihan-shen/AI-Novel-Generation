import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from sqlalchemy import text
from app.database import init_db
from app.routers import projects, outlines, settings, chapters, styles, reviews, ideas, config, outline_gen, search, agent

app = FastAPI(title="AI Novel Generation Tool")

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
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.include_router(projects.router)
from app.routers.projects import api_router as projects_api
app.include_router(projects_api)
app.include_router(outlines.router)
from app.routers.outlines import api_router as outlines_api
app.include_router(outlines_api)
app.include_router(settings.router)
app.include_router(chapters.router)
# app.include_router(brainstorming.router)  # DEPRECATED
app.include_router(styles.router)
app.include_router(reviews.router)
app.include_router(ideas.router)
app.include_router(config.router)
app.include_router(outline_gen.router)
app.include_router(search.router)
app.include_router(agent.router)


@app.get("/brainstorm")
async def brainstorm_redirect(project_id: str | None = None):
    """Redirect old /brainstorm page to agent chat."""
    if project_id:
        return RedirectResponse(url=f"/project/{project_id}/agent", status_code=302)
    return RedirectResponse(url="/", status_code=302)


templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.on_event("startup")
def on_startup():
    os.makedirs(BASE_DIR.parent / "data", exist_ok=True)
    init_db()
    from app.migrations import m001_token_usage_to_ai_call, m002_add_agent_task_columns
    from app.database import engine
    m001_token_usage_to_ai_call.run(engine)
    m002_add_agent_task_columns.run(engine)
    _recover_agent_tasks()


def _recover_agent_tasks():
    """Recover agent tasks that were interrupted by a restart."""
    from app.models.agent_task import AgentTask
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        running_tasks = db.query(AgentTask).filter(
            AgentTask.status.in_(["running", "waiting_user"])
        ).all()
        for task in running_tasks:
            if task.status == "waiting_user":
                task.status = "cancelled"
                task.completed_at = None
                from datetime import datetime
                task.completed_at = datetime.utcnow()
            else:
                task.status = "failed"
            task.orchestrator_state = "CANCELLED"
            db.commit()
            from app.models.agent_message import AgentMessage
            import uuid
            msg = AgentMessage(
                id=str(uuid.uuid4()),
                task_id=task.id,
                role="system",
                content=f"Task auto-cancelled on server restart. Previous state: {task.orchestrator_state}",
                message_type="error",
                sequence=9999,
            )
            db.add(msg)
            db.commit()
    finally:
        db.close()


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(request, "dashboard.html", {"request": request})


def _get_server_config():
    """Read host/port from DB config, falling back to env defaults."""
    try:
        from app.database import SessionLocal
        from app.services.config_service import ConfigService
        db = SessionLocal()
        cfg = ConfigService.get_all(db)
        db.close()
        return cfg.get("host", "0.0.0.0"), int(cfg.get("port", 8000))
    except Exception:
        return "0.0.0.0", 8000


def start():
    """Entry point for `novel-forge` CLI command."""
    import uvicorn
    host, port = _get_server_config()
    uvicorn.run("app.main:app", host=host, port=port)


# Auth middleware will be registered here in Phase 2+

if __name__ == "__main__":
    import uvicorn
    host, port = _get_server_config()
    uvicorn.run("app.main:app", host=host, port=port, reload=True)
