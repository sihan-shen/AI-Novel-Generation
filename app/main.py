import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.database import init_db
from app.routers import projects, outlines, settings, chapters, brainstorming, styles, reviews, ideas, config, outline_gen

app = FastAPI(title="AI Novel Generation Tool")
BASE_DIR = Path(__file__).parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.include_router(projects.router)
app.include_router(outlines.router)
app.include_router(settings.router)
app.include_router(chapters.router)
app.include_router(brainstorming.router)
app.include_router(styles.router)
app.include_router(reviews.router)
app.include_router(ideas.router)
app.include_router(config.router)
app.include_router(outline_gen.router)

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.on_event("startup")
def on_startup():
    os.makedirs(BASE_DIR.parent / "data", exist_ok=True)
    init_db()
    from app.migrations import m001_token_usage_to_ai_call
    from app.database import engine
    m001_token_usage_to_ai_call.run(engine)


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


if __name__ == "__main__":
    import uvicorn
    host, port = _get_server_config()
    uvicorn.run("app.main:app", host=host, port=port, reload=True)
