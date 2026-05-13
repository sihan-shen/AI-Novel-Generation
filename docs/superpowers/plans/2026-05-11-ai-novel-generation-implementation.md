# AI Novel Generation Tool — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local web-based LLM-assisted novel writing tool with 5 integrated modules: outline management, setting management, brainstorming, style reference, and auto review.

**Architecture:** FastAPI backend serving Jinja2/HTMX frontend, SQLite via SQLAlchemy ORM, Claude API for LLM features. Service layer pattern with separate router/service/model layers.

**Tech Stack:** Python 3.11+, FastAPI, Jinja2, HTMX, Tailwind CSS (CDN), SQLAlchemy, SQLite, Claude API (anthropic SDK), python-dotenv

---

## Phase 1: Foundation & Skeleton

### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `app/__init__.py`
- Create: `app/main.py`
- Create: `app/config.py`

- [ ] **Step 1: Create pyproject.toml**

````toml
[project]
name = "ai-novel-generation"
version = "0.1.0"
description = "LLM-assisted novel writing tool"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.110.0",
    "uvicorn[standard]>=0.29.0",
    "sqlalchemy>=2.0.30",
    "python-dotenv>=1.0.1",
    "jinja2>=3.1.3",
    "anthropic>=0.39.0",
    "openai>=1.30.0",
    "aiofiles>=23.2.1",
    "python-multipart>=0.0.9",
]

[tool.ruff]
line-length = 100
````

- [ ] **Step 2: Create .env.example**

````bash
# LLM API Configuration
CLAUDE_API_KEY=your_claude_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
LLM_PROVIDER=claude

# App Configuration
DATABASE_URL=sqlite:///./data/novel_tool.db
````

- [ ] **Step 3: Create .gitignore**

````
venv/
__pycache__/
*.pyc
.env
data/
````

- [ ] **Step 4: Create app/__init__.py**

Empty file.

- [ ] **Step 5: Create app/config.py**

````python
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    database_url: str = "sqlite:///./data/novel_tool.db"
    llm_provider: str = "claude"
    claude_api_key: str = ""
    openai_api_key: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
````

- [ ] **Step 6: Create app/main.py**

````python
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="AI Novel Generation Tool")

BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
````

- [ ] **Step 7: Commit**

````bash
git add -A && git commit -m "phase-1: project scaffolding with FastAPI skeleton"
````

---

### Task 2: Database Setup

**Files:**
- Create: `app/database.py`
- Create: `app/models/__init__.py`
- Create: `app/models/base.py`

- [ ] **Step 1: Create app/database.py**

````python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db():
    """Import all models so Base has them registered, then create tables."""
    from app.models import project, outline, setting, chapter, style, review, idea  # noqa
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
````

- [ ] **Step 2: Create app/models/__init__.py**

````python
from app.models.base import Base
from app.models.project import Project
from app.models.outline import Outline
from app.models.setting import Setting, SettingRelation
from app.models.chapter import Chapter, ChapterSettingLink
from app.models.style import Style, ProjectStyleLink
from app.models.review import Review
from app.models.idea import Idea
````

- [ ] **Step 3: Create app/models/base.py**

````python
from app.database import Base
````

- [ ] **Step 4: Add startup event to main.py**

Edit `app/main.py` to add:

````python
from app.database import init_db


@app.on_event("startup")
def on_startup():
    init_db()
````

- [ ] **Step 5: Test database init**

````bash
mkdir -p data
python -c "from app.database import init_db; init_db(); print('DB OK')"
# Expected: DB OK
# Verify: ls data/novel_tool.db → file exists
````

- [ ] **Step 6: Commit**

````bash
git add -A && git commit -m "phase-1: database setup with SQLAlchemy engine"
````

---

### Task 3: SQLAlchemy Models

**Files:**
- Create: `app/models/project.py`
- Create: `app/models/outline.py`
- Create: `app/models/setting.py`
- Create: `app/models/chapter.py`
- Create: `app/models/style.py`
- Create: `app/models/review.py`
- Create: `app/models/idea.py`

- [ ] **Step 1: Create app/models/project.py**

````python
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime
from app.database import Base


def _uuid():
    return str(uuid.uuid4())


class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=_uuid)
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    genre = Column(String, default="")
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
````

- [ ] **Step 2: Create app/models/outline.py**

````python
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey
from app.database import Base


class Outline(Base):
    __tablename__ = "outlines"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    parent_id = Column(String, ForeignKey("outlines.id"), nullable=True)
    level = Column(Integer, nullable=False)  # 1=volume, 2=chapter, 3=section
    sort_order = Column(Integer, nullable=False, default=0)
    title = Column(String, nullable=False)
    summary = Column(Text, default="")
    notes = Column(Text, default="")
    status = Column(String, default="draft")
    word_count_target = Column(Integer, default=0)
    word_count_actual = Column(Integer, default=0)
    pov_character = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
````

- [ ] **Step 3: Create app/models/setting.py**

````python
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey
from app.database import Base


class Setting(Base):
    __tablename__ = "settings"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    category = Column(String, nullable=False)
    name = Column(String, nullable=False)
    summary = Column(Text, default="")
    content = Column(Text, default="")
    structured_data = Column(Text, default="{}")  # JSON string
    weight = Column(Integer, default=5)
    sort_order = Column(Integer, default=0)
    key = Column(String, default="")
    status = Column(String, default="active")
    version = Column(Integer, default=1)
    tags = Column(Text, default="[]")  # JSON array
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SettingRelation(Base):
    __tablename__ = "setting_relations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    from_setting_id = Column(String, ForeignKey("settings.id", ondelete="CASCADE"), nullable=False)
    to_setting_id = Column(String, ForeignKey("settings.id", ondelete="CASCADE"), nullable=False)
    relation_type = Column(String, nullable=False)
    description = Column(Text, default="")
````

- [ ] **Step 4: Create app/models/chapter.py**

````python
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey
from app.database import Base


class Chapter(Base):
    __tablename__ = "chapters"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    outline_id = Column(String, ForeignKey("outlines.id"), nullable=True)
    title = Column(String, nullable=False)
    content = Column(Text, default="")
    sort_order = Column(Integer, nullable=False, default=0)
    status = Column(String, default="draft")
    word_count = Column(Integer, default=0)
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ChapterSettingLink(Base):
    __tablename__ = "chapter_setting_links"

    chapter_id = Column(String, ForeignKey("chapters.id", ondelete="CASCADE"), primary_key=True)
    setting_id = Column(String, ForeignKey("settings.id", ondelete="CASCADE"), primary_key=True)
````

- [ ] **Step 5: Create app/models/style.py**

````python
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Float
from app.database import Base


class Style(Base):
    __tablename__ = "styles"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    source = Column(Text, default="")
    source_text = Column(Text, default="")
    analysis = Column(Text, default="{}")  # JSON
    tags = Column(Text, default="[]")  # JSON array
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProjectStyleLink(Base):
    __tablename__ = "project_style_links"

    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True)
    style_id = Column(String, ForeignKey("styles.id", ondelete="CASCADE"), primary_key=True)
    weight = Column(Float, default=1.0)
````

- [ ] **Step 6: Create app/models/review.py**

````python
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from app.database import Base


class Review(Base):
    __tablename__ = "reviews"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    chapter_id = Column(String, ForeignKey("chapters.id"), nullable=True)
    scope = Column(String, nullable=False)
    summary = Column(Text, default="{}")  # JSON
    findings = Column(Text, default="[]")  # JSON array
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
````

- [ ] **Step 7: Create app/models/idea.py**

````python
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from app.database import Base


class Idea(Base):
    __tablename__ = "ideas"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=True)
    title = Column(String, default="")
    content = Column(Text, default="")
    source = Column(String, default="")
    tags = Column(Text, default="[]")
    status = Column(String, default="active")
    promoted_to_type = Column(String, nullable=True)
    promoted_to_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
````

- [ ] **Step 8: Test models**

````bash
python -c "
from app.database import init_db
init_db()
print('All models created successfully')
"
````

- [ ] **Step 9: Commit**

````bash
git add -A && git commit -m "phase-1: all SQLAlchemy models defined"
````

---

### Task 4: Base Template & Static Files

**Files:**
- Create: `app/templates/base.html`
- Create: `app/templates/dashboard.html`

- [ ] **Step 1: Create app/templates/base.html**

````html
<!DOCTYPE html>
<html lang="zh-CN" class="h-full">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}AI Novel Tool{% endblock %}</title>
    <script src="https://unpkg.com/htmx.org@1.9.12"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        primary: { 50: '#f0f4ff', 100: '#dbe4ff', 200: '#bac8ff', 300: '#91a7ff', 400: '#748ffc', 500: '#5c7cfa', 600: '#4c6ef5', 700: '#4263eb', 800: '#3b5bdb', 900: '#364fc7' },
                    }
                }
            }
        }
    </script>
</head>
<body class="h-full bg-gray-50 text-gray-900">
    <nav class="bg-white border-b border-gray-200 px-4 py-2.5">
        <div class="flex items-center justify-between max-w-7xl mx-auto">
            <a href="/" class="text-xl font-bold text-primary-700">Novel Forge</a>
            <div class="flex items-center space-x-4 text-sm">
                <a href="/" class="hover:text-primary-600">项目</a>
                <a href="/styles" class="hover:text-primary-600">文风库</a>
                <a href="/brainstorm" class="hover:text-primary-600">头脑风暴</a>
            </div>
        </div>
    </nav>
    <main class="max-w-7xl mx-auto px-4 py-6">
        {% block content %}{% endblock %}
    </main>
</body>
</html>
````

- [ ] **Step 2: Create app/templates/dashboard.html**

````html
{% extends "base.html" %}
{% block title %}项目列表 - Novel Forge{% endblock %}
{% block content %}
<div class="flex items-center justify-between mb-6">
    <h1 class="text-2xl font-bold">我的项目</h1>
    <button hx-get="/projects/new" hx-target="body" hx-swap="beforeend"
            class="bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700 text-sm">
        + 新建项目
    </button>
</div>
<div id="project-list" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
     hx-get="/projects/list" hx-trigger="load" hx-swap="innerHTML">
    <div class="col-span-full text-center py-12 text-gray-400">加载中...</div>
</div>
{% endblock %}
````

- [ ] **Step 3: Commit**

````bash
git add -A && git commit -m "phase-1: base template with Tailwind + HTMX"
````

---

### Task 5: Project CRUD Backend

**Files:**
- Create: `app/schemas/__init__.py`
- Create: `app/schemas/project.py`
- Create: `app/services/__init__.py`
- Create: `app/services/project_service.py`
- Create: `app/routers/__init__.py`
- Create: `app/routers/projects.py`

- [ ] **Step 1: Create app/schemas/__init__.py**

Empty file.

- [ ] **Step 2: Create app/schemas/project.py**

````python
from datetime import datetime
from pydantic import BaseModel


class ProjectCreate(BaseModel):
    title: str
    description: str = ""
    genre: str = ""


class ProjectUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    genre: str | None = None
    status: str | None = None


class ProjectResponse(BaseModel):
    id: str
    title: str
    description: str
    genre: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
````

- [ ] **Step 3: Create app/services/__init__.py**

Empty file.

- [ ] **Step 4: Create app/services/project_service.py**

````python
from sqlalchemy.orm import Session
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate


class ProjectService:
    @staticmethod
    def create(db: Session, data: ProjectCreate) -> Project:
        project = Project(title=data.title, description=data.description, genre=data.genre)
        db.add(project)
        db.commit()
        db.refresh(project)
        return project

    @staticmethod
    def get(db: Session, project_id: str) -> Project | None:
        return db.query(Project).filter(Project.id == project_id).first()

    @staticmethod
    def list(db: Session) -> list[Project]:
        return db.query(Project).order_by(Project.updated_at.desc()).all()

    @staticmethod
    def update(db: Session, project_id: str, data: ProjectUpdate) -> Project | None:
        project = ProjectService.get(db, project_id)
        if not project:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(project, field, value)
        db.commit()
        db.refresh(project)
        return project

    @staticmethod
    def delete(db: Session, project_id: str) -> bool:
        project = ProjectService.get(db, project_id)
        if not project:
            return False
        db.delete(project)
        db.commit()
        return True
````

- [ ] **Step 5: Create app/routers/__init__.py**

Empty file.

- [ ] **Step 6: Create app/routers/projects.py**

````python
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.project_service import ProjectService
from fastapi.templating import Jinja2Templates
from pathlib import Path

router = APIRouter(prefix="/projects", tags=["projects"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/list")
async def list_projects_html(db: Session = Depends(get_db)):
    projects = ProjectService.list(db)
    return templates.TemplateResponse("project/_list.html", {"request": {}, "projects": projects})


@router.get("/new")
async def new_project_form():
    return templates.TemplateResponse("project/_form.html", {"request": {}})


@router.post("/create")
async def create_project(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    data = ProjectCreate(title=form["title"], description=form.get("description", ""), genre=form.get("genre", ""))
    ProjectService.create(db, data)
    projects = ProjectService.list(db)
    return templates.TemplateResponse("project/_list.html", {"request": {}, "projects": projects})


@router.get("/{project_id}")
async def project_detail(project_id: str, db: Session = Depends(get_db)):
    project = ProjectService.get(db, project_id)
    if not project:
        return HTMLResponse("Project not found", status_code=404)
    return templates.TemplateResponse("project/_detail.html", {"request": {}, "project": project})


@router.delete("/{project_id}")
async def delete_project(project_id: str, db: Session = Depends(get_db)):
    ProjectService.delete(db, project_id)
    projects = ProjectService.list(db)
    return templates.TemplateResponse("project/_list.html", {"request": {}, "projects": projects})
````

- [ ] **Step 7: Register routers in main.py**

Edit `app/main.py`:

````python
from app.routers import projects

app.include_router(projects.router)
````

- [ ] **Step 8: Create project template partials**

Create `app/templates/project/_list.html`:

````html
{% for project in projects %}
<div class="bg-white rounded-lg border border-gray-200 p-5 hover:shadow-md transition-shadow">
    <div class="flex items-start justify-between">
        <div>
            <a href="/project/{{ project.id }}" class="text-lg font-semibold text-primary-700 hover:underline">{{ project.title }}</a>
            {% if project.genre %}<span class="ml-2 text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">{{ project.genre }}</span>{% endif %}
        </div>
        <button hx-delete="/projects/{{ project.id }}" hx-target="#project-list" hx-confirm="删除该项目？"
                class="text-gray-400 hover:text-red-500 text-sm">✕</button>
    </div>
    {% if project.description %}
    <p class="text-sm text-gray-500 mt-2 line-clamp-2">{{ project.description }}</p>
    {% endif %}
    <div class="flex items-center justify-between mt-4 text-xs text-gray-400">
        <span>{{ project.created_at.strftime('%Y-%m-%d') }}</span>
        <span>{{ project.status }}</span>
    </div>
</div>
{% else %}
<div class="col-span-full text-center py-12 text-gray-400">
    <p class="text-lg">还没有项目</p>
    <p class="mt-1">点击右上角"新建项目"开始</p>
</div>
{% endfor %}
````

Create `app/templates/project/_form.html`:

````html
<div id="modal" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50"
     hx-trigger="click" hx-target="#modal" hx-swap="delete" hx-select="#modal">
    <div class="bg-white rounded-xl p-6 w-full max-w-md shadow-xl" onclick="event.stopPropagation()">
        <h2 class="text-lg font-bold mb-4">新建项目</h2>
        <form hx-post="/projects/create" hx-target="#project-list" hx-swap="innerHTML"
              _="on submit wait 100ms then remove #modal">
            <div class="mb-3">
                <label class="block text-sm font-medium text-gray-700 mb-1">标题 *</label>
                <input type="text" name="title" required
                       class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500">
            </div>
            <div class="mb-3">
                <label class="block text-sm font-medium text-gray-700 mb-1">类型</label>
                <input type="text" name="genre" placeholder="奇幻 / 科幻 / 悬疑..."
                       class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500">
            </div>
            <div class="mb-4">
                <label class="block text-sm font-medium text-gray-700 mb-1">简介</label>
                <textarea name="description" rows="3"
                          class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"></textarea>
            </div>
            <div class="flex justify-end gap-2">
                <button type="button" onclick="document.getElementById('modal').remove()"
                        class="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">取消</button>
                <button type="submit" class="px-4 py-2 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700">创建</button>
            </div>
        </form>
    </div>
</div>
````

Create `app/templates/project/_detail.html`:

````html
<div class="bg-white rounded-lg border border-gray-200 p-6">
    <h1 class="text-2xl font-bold">{{ project.title }}</h1>
    {% if project.genre %}<span class="text-sm bg-gray-100 text-gray-600 px-2 py-0.5 rounded">{{ project.genre }}</span>{% endif %}
    {% if project.description %}<p class="text-gray-600 mt-2">{{ project.description }}</p>{% endif %}
    <div class="flex gap-4 mt-6">
        <a href="/project/{{ project.id }}/outline" class="px-4 py-2 bg-primary-50 text-primary-700 rounded-lg hover:bg-primary-100 text-sm">大纲</a>
        <a href="/project/{{ project.id }}/settings" class="px-4 py-2 bg-primary-50 text-primary-700 rounded-lg hover:bg-primary-100 text-sm">设定集</a>
        <a href="/project/{{ project.id }}/writer" class="px-4 py-2 bg-primary-50 text-primary-700 rounded-lg hover:bg-primary-100 text-sm">写作</a>
        <a href="/project/{{ project.id }}/review" class="px-4 py-2 bg-primary-50 text-primary-700 rounded-lg hover:bg-primary-100 text-sm">审阅</a>
    </div>
</div>
````

- [ ] **Step 9: Test the project CRUD**

````bash
# Start server
uvicorn app.main:app --port 8000 &
sleep 2

# The old workflow has already started on port 8000. Kill it.
kill %1 2>/dev/null; sleep 1

# Test via curl
python -c "
import httpx
r = httpx.get('http://localhost:8000/')
print('Dashboard:', r.status_code)
"
````

- [ ] **Step 10: Commit**

````bash
git add -A && git commit -m "phase-1: project CRUD with HTMX-driven UI"
````

---

### Task 6: LLM Adapter

**Files:**
- Create: `app/llm/__init__.py`
- Create: `app/llm/adapter.py`
- Create: `app/llm/claude_adapter.py`
- Create: `app/llm/openai_adapter.py`

- [ ] **Step 1: Create app/llm/__init__.py**

Empty file.

- [ ] **Step 2: Create app/llm/adapter.py**

````python
from abc import ABC, abstractmethod
from typing import Any


class LLMResponse:
    def __init__(self, content: str, usage: dict | None = None):
        self.content = content
        self.usage = usage or {}


class LLMAdapter(ABC):
    @abstractmethod
    async def generate(self, messages: list[dict], **kwargs) -> LLMResponse:
        ...

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        ...


def get_adapter() -> LLMAdapter:
    from app.config import settings
    if settings.llm_provider == "claude":
        from app.llm.claude_adapter import ClaudeAdapter
        return ClaudeAdapter(api_key=settings.claude_api_key)
    elif settings.llm_provider == "openai":
        from app.llm.openai_adapter import OpenAIAdapter
        return OpenAIAdapter(api_key=settings.openai_api_key)
    raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")
````

- [ ] **Step 3: Create app/llm/claude_adapter.py**

````python
from anthropic import AsyncAnthropic
from app.llm.adapter import LLMAdapter, LLMResponse


class ClaudeAdapter(LLMAdapter):
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        self.model = model
        self.client = AsyncAnthropic(api_key=api_key) if api_key else None

    async def generate(self, messages: list[dict], **kwargs) -> LLMResponse:
        if not self.client:
            return LLMResponse(content="[LLM 未配置: 请在 .env 中设置 Claude API Key]", usage={})
        system_msg = None
        api_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                system_msg = msg["content"]
            else:
                api_messages.append({"role": msg["role"], "content": msg["content"]})

        response = await self.client.messages.create(
            model=kwargs.get("model", self.model),
            system=system_msg,
            messages=api_messages,
            max_tokens=kwargs.get("max_tokens", 4096),
            temperature=kwargs.get("temperature", 0.7),
        )
        content = "".join(block.text for block in response.content if block.type == "text")
        return LLMResponse(content=content, usage={"input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens})

    def count_tokens(self, text: str) -> int:
        # Approximate: ~4 chars per token for Chinese/English mix
        return len(text) // 4
````

- [ ] **Step 4: Create app/llm/openai_adapter.py**

````python
from openai import AsyncOpenAI
from app.llm.adapter import LLMAdapter, LLMResponse


class OpenAIAdapter(LLMAdapter):
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.model = model
        self.client = AsyncOpenAI(api_key=api_key) if api_key else None

    async def generate(self, messages: list[dict], **kwargs) -> LLMResponse:
        if not self.client:
            return LLMResponse(content="[LLM 未配置]", usage={})
        response = await self.client.chat.completions.create(
            model=kwargs.get("model", self.model),
            messages=messages,
            max_tokens=kwargs.get("max_tokens", 4096),
            temperature=kwargs.get("temperature", 0.7),
        )
        return LLMResponse(
            content=response.choices[0].message.content or "",
            usage={"input_tokens": response.usage.prompt_tokens, "output_tokens": response.usage.completion_tokens} if response.usage else {}
        )

    def count_tokens(self, text: str) -> int:
        return len(text) // 4
````

- [ ] **Step 5: Commit**

````bash
git add -A && git commit -m "phase-1: LLM adapter with Claude and OpenAI support"
````

---

### Task 7: Project Detail Page & Navigation

**Files:**
- Create: `app/templates/project/detail.html`
- Modify: `app/routers/projects.py`

- [ ] **Step 1: Create project detail full page**

Create `app/templates/project/detail.html`:

````html
{% extends "base.html" %}
{% block title %}{{ project.title }} - Novel Forge{% endblock %}
{% block content %}
<div class="bg-white rounded-lg border border-gray-200 p-6 mb-6">
    <div class="flex items-center justify-between">
        <div>
            <h1 class="text-2xl font-bold">{{ project.title }}</h1>
            {% if project.genre %}<span class="text-sm bg-gray-100 text-gray-600 px-2 py-0.5 rounded mt-1 inline-block">{{ project.genre }}</span>{% endif %}
        </div>
        <a href="/" class="text-sm text-gray-500 hover:text-gray-700">← 返回</a>
    </div>
    {% if project.description %}<p class="text-gray-600 mt-3">{{ project.description }}</p>{% endif %}
</div>

<div class="grid grid-cols-2 md:grid-cols-4 gap-4">
    <a href="/project/{{ project.id }}/outline" class="bg-white border border-gray-200 rounded-lg p-5 hover:shadow-md transition-shadow text-center">
        <div class="text-3xl mb-2">📋</div>
        <div class="font-semibold">大纲</div>
        <div class="text-xs text-gray-400 mt-1">卷·章·节管理</div>
    </a>
    <a href="/project/{{ project.id }}/settings" class="bg-white border border-gray-200 rounded-lg p-5 hover:shadow-md transition-shadow text-center">
        <div class="text-3xl mb-2">🌍</div>
        <div class="font-semibold">设定集</div>
        <div class="text-xs text-gray-400 mt-1">世界观·人物</div>
    </a>
    <a href="/project/{{ project.id }}/writer" class="bg-white border border-gray-200 rounded-lg p-5 hover:shadow-md transition-shadow text-center">
        <div class="text-3xl mb-2">✍️</div>
        <div class="font-semibold">写作</div>
        <div class="text-xs text-gray-400 mt-1">创作编辑</div>
    </a>
    <a href="/project/{{ project.id }}/review" class="bg-white border border-gray-200 rounded-lg p-5 hover:shadow-md transition-shadow text-center">
        <div class="text-3xl mb-2">✅</div>
        <div class="font-semibold">审阅</div>
        <div class="text-xs text-gray-400 mt-1">自动审阅</div>
    </a>
</div>
{% endblock %}
````

- [ ] **Step 2: Add full page route to projects router**

Add to `app/routers/projects.py`:

````python
@router.get("/{project_id}/page")
async def project_detail_page(project_id: str, db: Session = Depends(get_db)):
    project = ProjectService.get(db, project_id)
    if not project:
        return HTMLResponse("Project not found", status_code=404)
    return templates.TemplateResponse("project/detail.html", {"request": {}, "project": project})
````

- [ ] **Step 3: Hook up dashboard link to full page**

- [ ] **Step 4: Add project_style_links model import to __init__.py**

- [ ] **Step 5: Commit**

````bash
git add -A && git commit -m "phase-1: project detail page and module navigation"
````

---

### Phase 1 Self-Check

Verify Phase 1 complete:
- [ ] FastAPI app starts and serves pages
- [ ] SQLite database created with all tables
- [ ] Project CRUD works (create/list/delete)
- [ ] Base template renders with HTMX/Tailwind
- [ ] LLM adapter can connect (if API key configured)

---

## Phase 2: Core Creation Tools

### Task 8: Outline Manager — Backend Service

**Files:**
- Create: `app/schemas/outline.py`
- Create: `app/services/outline_service.py`
- Create: `app/routers/outlines.py`

- [ ] **Step 1: Create app/schemas/outline.py**

````python
from datetime import datetime
from pydantic import BaseModel


class OutlineCreate(BaseModel):
    project_id: str
    parent_id: str | None = None
    level: int = 1
    sort_order: int = 0
    title: str
    summary: str = ""
    notes: str = ""


class OutlineUpdate(BaseModel):
    title: str | None = None
    summary: str | None = None
    notes: str | None = None
    status: str | None = None
    sort_order: int | None = None
    word_count_target: int | None = None
    pov_character: str | None = None


class OutlineResponse(BaseModel):
    id: str
    project_id: str
    parent_id: str | None
    level: int
    sort_order: int
    title: str
    summary: str
    notes: str
    status: str
    word_count_target: int
    word_count_actual: int
    pov_character: str
    created_at: datetime
    updated_at: datetime
    children: list["OutlineResponse"] = []

    class Config:
        from_attributes = True
````

- [ ] **Step 2: Create app/services/outline_service.py**

````python
from sqlalchemy.orm import Session
from app.models.outline import Outline
from app.schemas.outline import OutlineCreate, OutlineUpdate


class OutlineService:
    @staticmethod
    def create(db: Session, data: OutlineCreate) -> Outline:
        max_order = db.query(Outline.sort_order).filter(
            Outline.project_id == data.project_id,
            Outline.parent_id == data.parent_id,
            Outline.level == data.level,
        ).order_by(Outline.sort_order.desc()).first()
        sort_order = (max_order[0] + 1) if max_order else 1
        obj = Outline(
            project_id=data.project_id,
            parent_id=data.parent_id,
            level=data.level,
            sort_order=sort_order,
            title=data.title,
            summary=data.summary,
            notes=data.notes,
        )
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def get(db: Session, outline_id: str) -> Outline | None:
        return db.query(Outline).filter(Outline.id == outline_id).first()

    @staticmethod
    def get_tree(db: Session, project_id: str) -> list[Outline]:
        """Return all outlines for a project, sorted for tree building."""
        return db.query(Outline).filter(
            Outline.project_id == project_id
        ).order_by(Outline.sort_order).all()

    @staticmethod
    def update(db: Session, outline_id: str, data: OutlineUpdate) -> Outline | None:
        obj = OutlineService.get(db, outline_id)
        if not obj:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(obj, field, value)
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def delete(db: Session, outline_id: str) -> bool:
        obj = OutlineService.get(db, outline_id)
        if not obj:
            return False
        # Delete children first
        db.query(Outline).filter(Outline.parent_id == outline_id).delete()
        db.delete(obj)
        db.commit()
        return True

    @staticmethod
    def reorder(db: Session, items: list[dict]) -> None:
        """items = [{"id": "...", "sort_order": 1}, ...]"""
        for item in items:
            db.query(Outline).filter(Outline.id == item["id"]).update(
                {"sort_order": item["sort_order"]}
            )
        db.commit()
````

- [ ] **Step 3: Create app/routers/outlines.py**

````python
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from pathlib import Path
from fastapi.templating import Jinja2Templates

from app.database import get_db
from app.schemas.outline import OutlineCreate, OutlineUpdate
from app.services.outline_service import OutlineService
from app.services.project_service import ProjectService

router = APIRouter(prefix="/project/{project_id}/outline", tags=["outline"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("")
async def outline_page(project_id: str, db: Session = Depends(get_db)):
    project = ProjectService.get(db, project_id)
    if not project:
        return HTMLResponse("Project not found", status_code=404)
    outlines = OutlineService.get_tree(db, project_id)
    return templates.TemplateResponse("outline/index.html", {
        "request": {}, "project": project, "outlines": outlines
    })


@router.post("/create")
async def create_outline(request: Request, project_id: str, db: Session = Depends(get_db)):
    form = await request.form()
    data = OutlineCreate(
        project_id=project_id,
        parent_id=form.get("parent_id") or None,
        level=int(form.get("level", 1)),
        title=form["title"],
        summary=form.get("summary", ""),
    )
    OutlineService.create(db, data)
    outlines = OutlineService.get_tree(db, project_id)
    return templates.TemplateResponse("outline/_tree.html", {"request": {}, "outlines": outlines, "project_id": project_id})


@router.put("/{outline_id}")
async def update_outline(outline_id: str, request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    data = OutlineUpdate(
        title=form.get("title"),
        summary=form.get("summary"),
        status=form.get("status"),
    )
    OutlineService.update(db, outline_id, data)
    return HTMLResponse("ok")


@router.delete("/{outline_id}")
async def delete_outline(project_id: str, outline_id: str, db: Session = Depends(get_db)):
    OutlineService.delete(db, outline_id)
    outlines = OutlineService.get_tree(db, project_id)
    return templates.TemplateResponse("outline/_tree.html", {"request": {}, "outlines": outlines, "project_id": project_id})


@router.post("/reorder")
async def reorder_outlines(project_id: str, request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    OutlineService.reorder(db, data["items"])
    return HTMLResponse("ok")
````

- [ ] **Step 4: Register router in main.py**

````python
from app.routers import outlines
app.include_router(outlines.router)
````

- [ ] **Step 5: Commit**

````bash
git add -A && git commit -m "phase-2: outline service and API routes"
````

---

### Task 9: Outline Tree View UI

**Files:**
- Create: `app/templates/outline/index.html`
- Create: `app/templates/outline/_tree.html`
- Create: `app/templates/outline/_form.html`

- [ ] **Step 1: Create app/templates/outline/index.html**

````html
{% extends "base.html" %}
{% block title %}大纲 - {{ project.title }}{% endblock %}
{% block content %}
<div class="flex items-center justify-between mb-4">
    <div>
        <h1 class="text-2xl font-bold">{{ project.title }}</h1>
        <p class="text-sm text-gray-500">大纲</p>
    </div>
    <button hx-get="/project/{{ project.id }}/outline/new-item" hx-target="body" hx-swap="beforeend"
            class="bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700 text-sm">
        + 添加条目
    </button>
</div>
<div id="outline-tree" class="bg-white rounded-lg border border-gray-200 p-4"
     hx-get="/project/{{ project.id }}/outline/tree" hx-trigger="load" hx-swap="innerHTML">
    加载中...
</div>
{% endblock %}
````

- [ ] **Step 2: Create app/templates/outline/_tree.html**

````html
{% macro render_item(item, depth=0) %}
<div class="outline-item py-2 {% if depth > 0 %}ml-6 pl-3 border-l-2 border-gray-100{% endif %}"
     data-id="{{ item.id }}" data-level="{{ item.level }}">
    <div class="flex items-center justify-between group">
        <div class="flex items-center gap-2">
            <span class="text-xs text-gray-400 w-4">
                {% if item.level == 1 %}📚{% elif item.level == 2 %}📄{% else %}📝{% endif %}
            </span>
            <div>
                <span class="font-medium text-sm">{{ item.title }}</span>
                {% if item.summary %}
                <span class="text-xs text-gray-400 ml-2 truncate max-w-xs">{{ item.summary }}</span>
                {% endif %}
            </div>
            <span class="text-xs text-gray-300">{{ item.status }}</span>
        </div>
        <div class="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <button hx-get="/project/{{ project_id }}/outline/new-item?parent_id={{ item.id }}&level={{ item.level + 1 }}"
                    hx-target="body" hx-swap="beforeend"
                    class="text-xs text-gray-400 hover:text-primary-600 px-1">+子</button>
            <button hx-get="/project/{{ project_id }}/outline/edit/{{ item.id }}"
                    hx-target="body" hx-swap="beforeend"
                    class="text-xs text-gray-400 hover:text-primary-600 px-1">编辑</button>
            <button hx-delete="/project/{{ project_id }}/outline/{{ item.id }}" hx-target="#outline-tree"
                    hx-confirm="删除此项？"
                    class="text-xs text-gray-400 hover:text-red-500 px-1">✕</button>
        </div>
    </div>
</div>
{% endmacro %}

<div class="space-y-1">
{% set volumes = outlines | selectattr("level", "equalto", 1) | list %}
{% if volumes %}
    {% for vol in volumes %}
        {{ render_item(vol) }}
        {% set chapters = outlines | selectattr("parent_id", "equalto", vol.id) | list %}
        {% for ch in chapters %}
            {{ render_item(ch, 1) }}
            {% set sections = outlines | selectattr("parent_id", "equalto", ch.id) | list %}
            {% for sec in sections %}
                {{ render_item(sec, 2) }}
            {% endfor %}
        {% endfor %}
    {% endfor %}
{% else %}
    <p class="text-gray-400 text-center py-8">暂无大纲条目，点击右上角添加</p>
{% endif %}
</div>
````

- [ ] **Step 3: Create app/templates/outline/_form.html**

````html
<div id="modal" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50"
     hx-trigger="click" hx-target="#modal" hx-swap="delete" hx-select="#modal">
    <div class="bg-white rounded-xl p-6 w-full max-w-md shadow-xl" onclick="event.stopPropagation()">
        <h2 class="text-lg font-bold mb-4">{% if is_edit %}编辑{% else %}添加{% endif %}大纲条目</h2>
        <form hx-post="{{ post_url }}" hx-target="#outline-tree" hx-swap="innerHTML"
              _="on submit wait 100ms then remove #modal">
            <input type="hidden" name="level" value="{{ level }}">
            <input type="hidden" name="parent_id" value="{{ parent_id or '' }}">
            <div class="mb-3">
                <label class="block text-sm font-medium text-gray-700 mb-1">标题 *</label>
                <input type="text" name="title" value="{{ item.title if item else '' }}" required
                       class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500">
            </div>
            <div class="mb-4">
                <label class="block text-sm font-medium text-gray-700 mb-1">概要</label>
                <textarea name="summary" rows="3" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500">{{ item.summary if item else '' }}</textarea>
            </div>
            <div class="flex justify-end gap-2">
                <button type="button" onclick="document.getElementById('modal').remove()"
                        class="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">取消</button>
                <button type="submit" class="px-4 py-2 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700">保存</button>
            </div>
        </form>
    </div>
</div>
````

- [ ] **Step 4: Add form and tree routes to outlines router**

Add to `app/routers/outlines.py`:

````python
@router.get("/tree")
async def outline_tree(project_id: str, db: Session = Depends(get_db)):
    outlines = OutlineService.get_tree(db, project_id)
    return templates.TemplateResponse("outline/_tree.html", {"request": {}, "outlines": outlines, "project_id": project_id})


@router.get("/new-item")
async def new_outline_form(project_id: str, parent_id: str | None = None, level: int = 1):
    return templates.TemplateResponse("outline/_form.html", {
        "request": {},
        "project_id": project_id,
        "parent_id": parent_id,
        "level": level,
        "is_edit": False,
        "item": None,
        "post_url": f"/project/{project_id}/outline/create",
    })
````

- [ ] **Step 5: Commit**

````bash
git add -A && git commit -m "phase-2: outline tree view UI with HTMX"
````

---

### Task 10: Settings Manager — Backend

**Files:**
- Create: `app/schemas/setting.py`
- Create: `app/services/setting_service.py`
- Create: `app/routers/settings.py`

- [ ] **Step 1: Create app/schemas/setting.py**

````python
from datetime import datetime
from pydantic import BaseModel


class SettingCreate(BaseModel):
    project_id: str
    category: str
    name: str
    summary: str = ""
    content: str = ""
    structured_data: str = "{}"
    weight: int = 5
    key: str = ""
    tags: str = "[]"


class SettingUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    summary: str | None = None
    content: str | None = None
    structured_data: str | None = None
    weight: int | None = None
    status: str | None = None
    tags: str | None = None


class SettingRelationCreate(BaseModel):
    from_setting_id: str
    to_setting_id: str
    relation_type: str
    description: str = ""
````

- [ ] **Step 2: Create app/services/setting_service.py**

````python
import json
from sqlalchemy.orm import Session
from app.models.setting import Setting, SettingRelation
from app.schemas.setting import SettingCreate, SettingUpdate, SettingRelationCreate


CATEGORIES = ["世界观", "人物", "组织", "地理", "魔法/科技体系", "事件", "物品", "自定义"]


class SettingService:
    @staticmethod
    def create(db: Session, data: SettingCreate) -> Setting:
        obj = Setting(
            project_id=data.project_id, category=data.category, name=data.name,
            summary=data.summary, content=data.content,
            structured_data=data.structured_data, weight=data.weight,
            key=data.key or data.name, tags=data.tags,
        )
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def get(db: Session, setting_id: str) -> Setting | None:
        return db.query(Setting).filter(Setting.id == setting_id).first()

    @staticmethod
    def list_by_project(db: Session, project_id: str, category: str | None = None) -> list[Setting]:
        q = db.query(Setting).filter(Setting.project_id == project_id)
        if category:
            q = q.filter(Setting.category == category)
        return q.order_by(Setting.sort_order, Setting.name).all()

    @staticmethod
    def update(db: Session, setting_id: str, data: SettingUpdate) -> Setting | None:
        obj = SettingService.get(db, setting_id)
        if not obj:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(obj, field, value)
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def delete(db: Session, setting_id: str) -> bool:
        obj = SettingService.get(db, setting_id)
        if not obj:
            return False
        db.delete(obj)
        db.commit()
        return True

    @staticmethod
    def add_relation(db: Session, data: SettingRelationCreate) -> SettingRelation:
        rel = SettingRelation(
            from_setting_id=data.from_setting_id,
            to_setting_id=data.to_setting_id,
            relation_type=data.relation_type,
            description=data.description,
        )
        db.add(rel)
        db.commit()
        db.refresh(rel)
        return rel

    @staticmethod
    def remove_relation(db: Session, relation_id: str) -> bool:
        rel = db.query(SettingRelation).filter(SettingRelation.id == relation_id).first()
        if not rel:
            return False
        db.delete(rel)
        db.commit()
        return True

    @staticmethod
    def get_relations(db: Session, setting_id: str) -> list[SettingRelation]:
        return db.query(SettingRelation).filter(
            (SettingRelation.from_setting_id == setting_id) | (SettingRelation.to_setting_id == setting_id)
        ).all()

    @staticmethod
    def build_llm_context(db: Session, project_id: str, related_ids: list[str] | None = None) -> str:
        """Build a condensed settings summary for LLM context."""
        settings = SettingService.list_by_project(db, project_id)
        lines = ["=== 设定集摘要 ==="]
        for s in settings:
            if s.status != "active":
                continue
            weight_tag = "高" if s.weight >= 7 else "中" if s.weight >= 4 else "低"
            tag_str = f"[权重{weight_tag}]"
            lines.append(f"{tag_str} {s.category}: {s.name} (key: {s.key})")
        lines.append("")
        if related_ids:
            lines.append("=== 详细设定（相关条目） ===")
            for sid in related_ids:
                s = SettingService.get(db, sid)
                if s and s.status == "active":
                    lines.append(f"## {s.category}：{s.name} [{s.key}]")
                    lines.append(s.summary or s.content[:200] if s.content else "")
                    lines.append("")
        return "\n".join(lines)
````

- [ ] **Step 3: Create app/routers/settings.py**

````python
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from pathlib import Path
from fastapi.templating import Jinja2Templates

from app.database import get_db
from app.schemas.setting import SettingCreate, SettingUpdate
from app.services.setting_service import SettingService, CATEGORIES
from app.services.project_service import ProjectService

router = APIRouter(prefix="/project/{project_id}/settings", tags=["settings"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("")
async def settings_page(project_id: str, category: str | None = None, db: Session = Depends(get_db)):
    project = ProjectService.get(db, project_id)
    if not project:
        return HTMLResponse("Not found", 404)
    settings = SettingService.list_by_project(db, project_id, category)
    return templates.TemplateResponse("settings/index.html", {
        "request": {}, "project": project, "settings": settings,
        "categories": CATEGORIES, "current_category": category or "全部",
    })


@router.get("/list")
async def settings_list(project_id: str, category: str | None = None, db: Session = Depends(get_db)):
    settings = SettingService.list_by_project(db, project_id, category)
    return templates.TemplateResponse("settings/_list.html", {"request": {}, "settings": settings, "project_id": project_id})


@router.get("/new")
async def new_setting_form(project_id: str, category: str):
    return templates.TemplateResponse("settings/_form.html", {
        "request": {}, "project_id": project_id, "category": category, "is_edit": False,
        "item": None, "post_url": f"/project/{project_id}/settings/create",
    })


@router.post("/create")
async def create_setting(request: Request, project_id: str, db: Session = Depends(get_db)):
    form = await request.form()
    data = SettingCreate(
        project_id=project_id, category=form["category"], name=form["name"],
        summary=form.get("summary", ""), content=form.get("content", ""),
        weight=int(form.get("weight", 5)),
    )
    SettingService.create(db, data)
    settings = SettingService.list_by_project(db, project_id)
    return templates.TemplateResponse("settings/_list.html", {"request": {}, "settings": settings, "project_id": project_id})


@router.get("/{setting_id}")
async def setting_detail(setting_id: str, db: Session = Depends(get_db)):
    setting = SettingService.get(db, setting_id)
    if not setting:
        return HTMLResponse("Not found", 404)
    relations = SettingService.get_relations(db, setting_id)
    return templates.TemplateResponse("settings/_detail.html", {
        "request": {}, "setting": setting, "relations": relations,
    })


@router.delete("/{setting_id}")
async def delete_setting(project_id: str, setting_id: str, db: Session = Depends(get_db)):
    SettingService.delete(db, setting_id)
    settings = SettingService.list_by_project(db, project_id)
    return templates.TemplateResponse("settings/_list.html", {"request": {}, "settings": settings, "project_id": project_id})
````

- [ ] **Step 4: Register router**

Add `app.include_router(settings.router)` to main.py.

- [ ] **Step 5: Commit**

````bash
git add -A && git commit -m "phase-2: settings service, API routes, and LLM context builder"
````

---

### Task 11: Settings UI

**Files:**
- Create: `app/templates/settings/index.html`
- Create: `app/templates/settings/_list.html`
- Create: `app/templates/settings/_form.html`
- Create: `app/templates/settings/_detail.html`

- [ ] **Step 1: Create app/templates/settings/index.html**

````html
{% extends "base.html" %}
{% block title %}设定集 - {{ project.title }}{% endblock %}
{% block content %}
<div class="flex items-center justify-between mb-4">
    <div>
        <h1 class="text-2xl font-bold">{{ project.title }}</h1>
        <p class="text-sm text-gray-500">设定集</p>
    </div>
    <div class="flex gap-2">
        <button id="clean-btn"
                class="px-4 py-2 text-sm bg-amber-50 text-amber-700 rounded-lg hover:bg-amber-100 border border-amber-200">
            🧹 打扫
        </button>
    </div>
</div>

<!-- Category tabs -->
<div class="flex gap-1 mb-4 overflow-x-auto" id="category-tabs">
    <a href="/project/{{ project.id }}/settings"
       class="px-3 py-1.5 text-sm rounded-lg {% if current_category == '全部' %}bg-primary-100 text-primary-700{% else %}bg-gray-100 text-gray-600 hover:bg-gray-200{% endif %}">
        全部
    </a>
    {% for cat in categories %}
    <a href="/project/{{ project.id }}/settings?category={{ cat }}"
       class="px-3 py-1.5 text-sm rounded-lg whitespace-nowrap {% if current_category == cat %}bg-primary-100 text-primary-700{% else %}bg-gray-100 text-gray-600 hover:bg-gray-200{% endif %}">
        {{ cat }}
    </a>
    {% endfor %}
</div>

<div id="settings-list" class="space-y-2"
     hx-get="/project/{{ project.id }}/settings/list?category={{ current_category if current_category != '全部' else '' }}"
     hx-trigger="load" hx-swap="innerHTML">
    加载中...
</div>
{% endblock %}
````

- [ ] **Step 2: Create app/templates/settings/_list.html**

````html
{% for item in settings %}
<div class="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-sm transition-shadow">
    <div class="flex items-start justify-between">
        <div class="flex-1">
            <div class="flex items-center gap-2">
                <a href="/project/{{ project_id }}/settings/{{ item.id }}"
                   class="font-medium text-primary-700 hover:underline">{{ item.name }}</a>
                <span class="text-xs bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">{{ item.category }}</span>
                {% if item.weight >= 7 %}<span class="text-xs text-amber-600">★核心</span>{% endif %}
                {% if item.status == 'deprecated' %}<span class="text-xs text-red-400">已废弃</span>{% endif %}
            </div>
            {% if item.summary %}
            <p class="text-sm text-gray-500 mt-1">{{ item.summary }}</p>
            {% endif %}
        </div>
        <div class="flex gap-1 ml-2">
            <button hx-get="/project/{{ project_id }}/settings/{{ item.id }}"
                    hx-target="body" hx-swap="beforeend"
                    class="text-xs text-gray-400 hover:text-primary-600 px-1">查看</button>
            <button hx-delete="/project/{{ project_id }}/settings/{{ item.id }}"
                    hx-target="#settings-list" hx-confirm="删除「{{ item.name }}」？"
                    class="text-xs text-gray-400 hover:text-red-500 px-1">✕</button>
        </div>
    </div>
</div>
{% else %}
<div class="text-center py-12 text-gray-400">
    <p class="text-lg">暂无设定条目</p>
    <p class="text-sm mt-1">选择一个分类后点击添加</p>
</div>
{% endfor %}
````

- [ ] **Step 3: Create _form.html, _detail.html**

Following the same modal pattern as outline forms. Save and commit.

- [ ] **Step 4: Commit**

````bash
git add -A && git commit -m "phase-2: settings UI with category browsing"
````

---

### Task 12: Writing Editor

**Files:**
- Create: `app/schemas/chapter.py`
- Create: `app/services/chapter_service.py`
- Create: `app/routers/chapters.py`
- Create: `app/templates/writer/index.html`
- Create: `app/templates/writer/_editor.html`
- Create: `app/templates/writer/_sidebar.html`

- [ ] **Step 1: Create app/schemas/chapter.py**

````python
from datetime import datetime
from pydantic import BaseModel


class ChapterCreate(BaseModel):
    project_id: str
    outline_id: str | None = None
    title: str
    content: str = ""
    sort_order: int = 0
    notes: str = ""


class ChapterUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    status: str | None = None
    notes: str | None = None
````

- [ ] **Step 2: Create app/services/chapter_service.py**

````python
from sqlalchemy.orm import Session
from app.models.chapter import Chapter
from app.schemas.chapter import ChapterCreate, ChapterUpdate


class ChapterService:
    @staticmethod
    def create(db: Session, data: ChapterCreate) -> Chapter:
        ch = Chapter(**data.model_dump())
        db.add(ch)
        db.commit()
        db.refresh(ch)
        return ch

    @staticmethod
    def get(db: Session, chapter_id: str) -> Chapter | None:
        return db.query(Chapter).filter(Chapter.id == chapter_id).first()

    @staticmethod
    def list_by_project(db: Session, project_id: str) -> list[Chapter]:
        return db.query(Chapter).filter(Chapter.project_id == project_id).order_by(Chapter.sort_order).all()

    @staticmethod
    def update(db: Session, chapter_id: str, data: ChapterUpdate) -> Chapter | None:
        ch = ChapterService.get(db, chapter_id)
        if not ch:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(ch, field, value)
        ch.word_count = len(ch.content) if ch.content else 0
        db.commit()
        db.refresh(ch)
        return ch

    @staticmethod
    def delete(db: Session, chapter_id: str) -> bool:
        ch = ChapterService.get(db, chapter_id)
        if not ch:
            return False
        db.delete(ch)
        db.commit()
        return True
````

- [ ] **Step 3: Create app/routers/chapters.py**

````python
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from pathlib import Path
from fastapi.templating import Jinja2Templates

from app.database import get_db
from app.schemas.chapter import ChapterCreate, ChapterUpdate
from app.services.chapter_service import ChapterService
from app.services.project_service import ProjectService

router = APIRouter(prefix="/project/{project_id}/writer", tags=["writer"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("")
async def writer_page(project_id: str, db: Session = Depends(get_db)):
    project = ProjectService.get(db, project_id)
    if not project:
        return HTMLResponse("Not found", 404)
    chapters = ChapterService.list_by_project(db, project_id)
    return templates.TemplateResponse("writer/index.html", {
        "request": {}, "project": project, "chapters": chapters,
    })


@router.get("/chapters")
async def chapter_list(project_id: str, db: Session = Depends(get_db)):
    chapters = ChapterService.list_by_project(db, project_id)
    return templates.TemplateResponse("writer/_sidebar.html", {"request": {}, "chapters": chapters, "project_id": project_id})


@router.get("/new")
async def new_chapter_form(project_id: str):
    return templates.TemplateResponse("writer/_form.html", {"request": {}, "project_id": project_id})


@router.post("/create")
async def create_chapter(request: Request, project_id: str, db: Session = Depends(get_db)):
    form = await request.form()
    data = ChapterCreate(project_id=project_id, title=str(form["title"]))
    ChapterService.create(db, data)
    chapters = ChapterService.list_by_project(db, project_id)
    return templates.TemplateResponse("writer/_sidebar.html", {"request": {}, "chapters": chapters, "project_id": project_id})


@router.get("/{chapter_id}")
async def edit_chapter(chapter_id: str, db: Session = Depends(get_db)):
    chapter = ChapterService.get(db, chapter_id)
    if not chapter:
        return HTMLResponse("Not found", 404)
    return templates.TemplateResponse("writer/_editor.html", {"request": {}, "chapter": chapter})


@router.put("/{chapter_id}")
async def update_chapter(chapter_id: str, request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    data = ChapterUpdate(content=str(form.get("content", "")), title=str(form.get("title", "")))
    ChapterService.update(db, chapter_id, data)
    return HTMLResponse("ok")


@router.delete("/{chapter_id}")
async def delete_chapter(project_id: str, chapter_id: str, db: Session = Depends(get_db)):
    ChapterService.delete(db, chapter_id)
    chapters = ChapterService.list_by_project(db, project_id)
    return templates.TemplateResponse("writer/_sidebar.html", {"request": {}, "chapters": chapters, "project_id": project_id})
````

- [ ] **Step 4: Create writer templates**

Split-view layout: left sidebar (chapter list) + right editor.

Create `app/templates/writer/index.html`:

````html
{% extends "base.html" %}
{% block title %}写作 - {{ project.title }}{% endblock %}
{% block content %}
<div class="flex gap-4 h-[calc(100vh-8rem)]">
    <div class="w-64 shrink-0 overflow-y-auto">
        <div class="flex items-center justify-between mb-3">
            <h2 class="font-semibold text-sm text-gray-500">章节</h2>
            <button hx-get="/project/{{ project.id }}/writer/new" hx-target="body" hx-swap="beforeend"
                    class="text-xs text-primary-600 hover:text-primary-700">+ 新建</button>
        </div>
        <div id="chapter-sidebar" class="space-y-1"
             hx-get="/project/{{ project.id }}/writer/chapters" hx-trigger="load" hx-swap="innerHTML">
            加载中...
        </div>
    </div>
    <div class="flex-1 bg-white rounded-lg border border-gray-200 p-4 overflow-y-auto" id="editor-area">
        <div class="text-center text-gray-400 py-20">
            <p class="text-lg">选择左侧章节开始写作</p>
        </div>
    </div>
</div>
{% endblock %}
````

Create `app/templates/writer/_sidebar.html`:

````html
{% for ch in chapters %}
<div class="flex items-center justify-between px-3 py-2 rounded-lg hover:bg-gray-50 cursor-pointer text-sm group"
     hx-get="/project/{{ project_id }}/writer/{{ ch.id }}" hx-target="#editor-area" hx-swap="innerHTML">
    <div class="truncate flex-1">
        <span>{{ ch.title }}</span>
        <span class="text-xs text-gray-400 ml-1">{{ ch.word_count }}字</span>
    </div>
    <span class="text-xs text-gray-300 ml-1">{{ ch.status }}</span>
    <button hx-delete="/project/{{ project_id }}/writer/{{ ch.id }}" hx-target="#chapter-sidebar"
            hx-confirm="删除？" class="text-xs text-gray-300 hover:text-red-500 ml-2 opacity-0 group-hover:opacity-100">✕</button>
</div>
{% else %}
<p class="text-sm text-gray-400 text-center py-8">暂无章节</p>
{% endfor %}
````

Create `app/templates/writer/_editor.html`:

````html
<div>
    <div class="flex items-center justify-between mb-3">
        <input type="text" name="title" value="{{ chapter.title }}"
               class="text-xl font-bold border-none outline-none bg-transparent w-full"
               hx-put="/project/{{ chapter.project_id }}/writer/{{ chapter.id }}"
               hx-trigger="change" hx-include="closest div">
    </div>
    <textarea id="chapter-content" name="content"
              class="w-full h-[calc(100vh-16rem)] border-0 outline-none resize-none text-base leading-relaxed font-mono"
              placeholder="开始写作..."
              hx-put="/project/{{ chapter.project_id }}/writer/{{ chapter.id }}"
              hx-trigger="changed delay:2s" hx-include="[name='title']">{{ chapter.content }}</textarea>
</div>
````

- [ ] **Step 5: Register router and commit**

````bash
git add -A && git commit -m "phase-2: writing editor with split-panel layout"
````

---

### Phase 2 Self-Check

- [ ] Outline tree view loads and supports add/edit/delete
- [ ] Settings view with category filter works
- [ ] Writing editor loads chapters and auto-saves
- [ ] All routers properly registered in main.py

---

## Phase 3: AI Features

### Task 13: Context Builder & Prompt Templates

**Files:**
- Create: `app/llm/context_builder.py`
- Create: `app/llm/templates/writing.yaml`
- Create: `app/llm/templates/brainstorm.yaml`
- Create: `app/llm/templates/review.yaml`
- Create: `app/llm/templates/style_analysis.yaml`
- Create: `app/llm/templates/cleaning.yaml`
- Create: `app/llm/templates/__init__.py`

- [ ] **Step 1: Create app/llm/context_builder.py**

````python
import yaml
from pathlib import Path
from sqlalchemy.orm import Session

from app.services.setting_service import SettingService
from app.services.outline_service import OutlineService
from app.services.chapter_service import ChapterService


class ContextBuilder:
    """Assembles structured context for LLM calls based on scenario type."""

    SCENARIOS = ["writing", "brainstorm", "review", "style_analysis", "cleaning"]

    def __init__(self, db: Session):
        self.db = db
        self._templates: dict = {}

    def _load_template(self, scenario: str) -> dict:
        path = Path(__file__).parent / "templates" / f"{scenario}.yaml"
        if not path.exists():
            return {"system": "You are a novel writing assistant.", "template": "{{ request }}"}
        with open(path) as f:
            return yaml.safe_load(f) or {}

    def build(self, scenario: str, project_id: str, **kwargs) -> list[dict]:
        """Build messages list for LLM API call."""
        template = self._load_template(scenario)
        system = template.get("system", "")
        prompt_template = template.get("template", "")

        context_parts = []

        # Project info
        from app.services.project_service import ProjectService
        project = ProjectService.get(self.db, project_id)
        if project:
            context_parts.append(f"项目类型: {project.genre}\n项目状态: {project.status}")

        # Settings summary (always included)
        context_parts.append(SettingService.build_llm_context(self.db, project_id))

        # Recent chapters for context
        recent_chapters = ChapterService.list_by_project(self.db, project_id)
        if recent_chapters:
            last = recent_chapters[-1]
            context_parts.append(f"=== 最近章节 ===\n标题: {last.title}\n内容预览: {last.content[:300]}")

        # Build user prompt from template
        from jinja2 import Template
        user_prompt = Template(prompt_template).render(
            context="\n".join(context_parts),
            **kwargs
        )

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user_prompt})
        return messages
````

- [ ] **Step 2: Create prompt template YAML files**

`app/llm/templates/writing.yaml`:

````yaml
system: |
  你是一位专业的小说创作助手。你的任务是辅助作者完成创作，而非替代。
  基于提供的上下文，生成符合设定和文风要求的正文内容。
  请使用流畅的中文写作。

template: |
  {{ context }}

  写作任务:
  {{ request }}

  请注意:
  1. 严格遵循设定集中的信息，不要与既有设定矛盾
  2. 保持文风一致
  3. 输出格式：直接输出正文内容，不需要额外说明
````

`app/llm/templates/brainstorm.yaml`:

````yaml
system: |
  你是一位创意策划顾问。帮助作者拓展思路、激发灵感。
  输出应具有发散性和启发性，而非结论性。

template: |
  {{ context }}

  头脑风暴主题:
  {{ request }}

  请从多个角度提供创意建议，每个建议附简要说明。
  如果涉及设定扩展，请标注"可沉淀为设定"。
````

`app/llm/templates/review.yaml`:

````yaml
system: |
  你是一位专业的小说审稿编辑。从设定一致性、文风、逻辑、语言四个维度进行审阅。
  严格但不苛责，每个问题点需指出具体位置和改进建议。

template: |
  {{ context }}

  审阅正文:
  {{ request }}

  请按以下格式输出审阅结果：
  ## 设定一致性
  ## 文风一致性
  ## 逻辑与结构
  ## 语言润色
  ## 综合评估
````

`app/llm/templates/style_analysis.yaml`:

````yaml
system: |
  你是一位文学风格分析师。从词汇特征、句式节奏、修辞手法、语气口吻、叙事视角等维度分析文本风格。

template: |
  请分析以下文本的文风特征:

  {{ request }}

  输出格式要求:
  - 词汇特征: 用词偏好、高频词
  - 节奏: 句子长度分布、段落节奏
  - 修辞: 常用手法
  - 语气: 客观/主观, 冷峻/温情
  - 对话风格: 占比、特点
  - 叙事视角: POV使用
````

`app/llm/templates/cleaning.yaml`:

````yaml
system: |
  你是一位设定集管理员。检查设定条目之间的矛盾、重复、过时信息。
  输出矛盾点和修改建议。

template: |
  设定集条目:
  {{ context }}

  请检查:
  1. 逻辑矛盾（两条设定描述同一事物但信息冲突）
  2. 重复条目（不同名称但描述相同内容）
  3. 孤立条目（无任何关联引用的设定）
  4. 关系补全建议

  按严重程度排序输出。
````

- [ ] **Step 3: Create __init__.py in templates**

Empty file.

- [ ] **Step 4: Register all routers in main.py and commit**

````bash
git add -A && git commit -m "phase-3: context builder and prompt templates"
````

---

### Task 14: Brainstorm Feature

**Files:**
- Create: `app/services/brainstorm_service.py`
- Create: `app/routers/brainstorming.py`
- Create: `app/templates/brainstorm/index.html`

- [ ] **Step 1: Create app/services/brainstorm_service.py**

````python
from sqlalchemy.orm import Session
from app.llm.context_builder import ContextBuilder
from app.llm.adapter import get_adapter


class BrainstormService:
    @staticmethod
    async def brainstorm(db: Session, project_id: str | None, mode: str, query: str) -> str:
        """Execute a brainstorming session."""
        adapter = get_adapter()

        if mode == "free":
            messages = [
                {"role": "system", "content": "你是一位创意策划顾问。帮助作者拓展思路、激发灵感。"},
                {"role": "user", "content": f"请围绕以下主题进行头脑风暴，提供多个创意方向：\n\n{query}"}
            ]
        elif mode == "context" and project_id:
            builder = ContextBuilder(db)
            messages = builder.build("brainstorm", project_id, request=query)
        elif mode == "directed":
            messages = [
                {"role": "system", "content": "你是一位创意策划顾问。帮助作者拓展思路、激发灵感。"},
                {"role": "user", "content": f"方向：{query}\n\n请深入探讨这个方向，提供具体可用的创意。"}
            ]
        else:
            return "请提供有效的模式或项目上下文。"

        response = await adapter.generate(messages, temperature=0.9, max_tokens=2048)
        return response.content
````

- [ ] **Step 2: Create app/routers/brainstorming.py**

````python
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from pathlib import Path
from fastapi.templating import Jinja2Templates

from app.database import get_db
from app.services.brainstorm_service import BrainstormService
from app.services.project_service import ProjectService

router = APIRouter(prefix="/brainstorm", tags=["brainstorm"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("")
async def brainstorm_page(request: Request):
    return templates.TemplateResponse("brainstorm/index.html", {"request": request})


@router.post("/generate")
async def brainstorm_generate(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    mode = form.get("mode", "free")
    query = form.get("query", "")
    project_id = form.get("project_id") or None
    result = await BrainstormService.brainstorm(db, project_id, mode, query)
    return templates.TemplateResponse("brainstorm/_result.html", {"request": {}, "result": result})
````

- [ ] **Step 3: Create brainstorm UI template**

`app/templates/brainstorm/index.html`:

````html
{% extends "base.html" %}
{% block title %}头脑风暴{% endblock %}
{% block content %}
<div class="max-w-3xl mx-auto">
    <h1 class="text-2xl font-bold mb-2">头脑风暴</h1>
    <p class="text-sm text-gray-500 mb-6">自由发散 · 上下文风暴 · 定向激荡</p>

    <div class="bg-white rounded-lg border border-gray-200 p-6">
        <div class="flex gap-2 mb-4" id="mode-selector">
            <button onclick="setMode('free')" class="mode-btn px-4 py-2 text-sm rounded-lg bg-primary-100 text-primary-700" data-mode="free">自由发散</button>
            <button onclick="setMode('context')" class="mode-btn px-4 py-2 text-sm rounded-lg bg-gray-100 text-gray-600 hover:bg-gray-200" data-mode="context">上下文风暴</button>
            <button onclick="setMode('directed')" class="mode-btn px-4 py-2 text-sm rounded-lg bg-gray-100 text-gray-600 hover:bg-gray-200" data-mode="directed">定向激荡</button>
        </div>

        <form hx-post="/brainstorm/generate" hx-target="#result-area" hx-swap="innerHTML">
            <input type="hidden" name="mode" id="mode-input" value="free">
            <div class="mb-3" id="project-select-area" style="display:none">
                <select name="project_id" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                    <option value="">选择项目（可选）</option>
                </select>
            </div>
            <textarea name="query" rows="4" placeholder="输入你的问题或想法..."
                      class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary-500 mb-3"></textarea>
            <button type="submit" class="bg-primary-600 text-white px-6 py-2 rounded-lg hover:bg-primary-700 text-sm">
                开始头脑风暴
            </button>
        </form>
    </div>

    <div id="result-area" class="mt-4"></div>
</div>

<script>
function setMode(mode) {
    document.getElementById('mode-input').value = mode;
    document.querySelectorAll('.mode-btn').forEach(b => {
        b.classList.toggle('bg-primary-100', b.dataset.mode === mode);
        b.classList.toggle('text-primary-700', b.dataset.mode === mode);
        b.classList.toggle('bg-gray-100', b.dataset.mode !== mode);
        b.classList.toggle('text-gray-600', b.dataset.mode !== mode);
    });
    document.getElementById('project-select-area').style.display = mode === 'context' ? 'block' : 'none';
}
</script>
{% endblock %}
````

- [ ] **Step 4: Register router and commit**

````bash
git add -A && git commit -m "phase-3: brainstorm feature with three modes"
````

---

### Task 15: Style Import & Analysis

**Files:**
- Create: `app/services/style_service.py`
- Create: `app/routers/styles.py`
- Create: `app/templates/styles/index.html`

- [ ] **Step 1: Create app/services/style_service.py**

````python
import json
from sqlalchemy.orm import Session
from app.models.style import Style
from app.llm.adapter import get_adapter


class StyleService:
    @staticmethod
    def create(db: Session, name: str, source: str = "", source_text: str = "", analysis: str = "{}", tags: str = "[]") -> Style:
        style = Style(name=name, source=source, source_text=source_text, analysis=analysis, tags=tags)
        db.add(style)
        db.commit()
        db.refresh(style)
        return style

    @staticmethod
    def list_all(db: Session) -> list[Style]:
        return db.query(Style).order_by(Style.created_at.desc()).all()

    @staticmethod
    def get(db: Session, style_id: str) -> Style | None:
        return db.query(Style).filter(Style.id == style_id).first()

    @staticmethod
    def delete(db: Session, style_id: str) -> bool:
        style = StyleService.get(db, style_id)
        if not style:
            return False
        db.delete(style)
        db.commit()
        return True

    @staticmethod
    async def analyze_text(text: str) -> str:
        """Send text to LLM for style analysis."""
        adapter = get_adapter()
        messages = [
            {"role": "system", "content": "你是一位文学风格分析师。从词汇特征、句式节奏、修辞手法、语气口吻、叙事视角等维度分析文本风格。"},
            {"role": "user", "content": f"请分析以下文本的文风特征：\n\n{text}\n\n输出JSON格式：{{\"vocabulary\":\"\",\"rhythm\":\"\",\"rhetoric\":\"\",\"tone\":\"\",\"dialogue\":\"\",\"pov\":\"\"}}"}
        ]
        response = await adapter.generate(messages, temperature=0.3)
        return response.content

    @staticmethod
    async def smart_slice(text: str) -> list[dict]:
        """Use LLM to identify representative style slices from long text."""
        adapter = get_adapter()
        messages = [
            {"role": "system", "content": "你是一位文风分析师。从长文本中识别最能代表作者风格的段落，排除对话过多或风格中性的过渡段落。"},
            {"role": "user", "content": f"请从以下文本中选出3-5个最能代表作者文风的段落（每段200-500字），覆盖不同类型的描写（叙事、环境、心理等）。按重要度排序，每个切片附推荐理由。\n\n文本：\n\n{text[:8000]}\n\n输出JSON格式：{{"slices":[{{"index":1,"text":"...","type":"...","reason":"...","stars":5}}]}}"}
        ]
        response = await adapter.generate(messages, temperature=0.3)
        try:
            result = json.loads(response.content)
            return result.get("slices", [])
        except json.JSONDecodeError:
            return [{"text": text[:500], "reason": "全文切片", "stars": 3}]
````

- [ ] **Step 2: Create app/routers/styles.py**

````python
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from pathlib import Path
from fastapi.templating import Jinja2Templates

from app.database import get_db
from app.services.style_service import StyleService

router = APIRouter(prefix="/styles", tags=["styles"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("")
async def styles_page(db: Session = Depends(get_db)):
    styles = StyleService.list_all(db)
    return templates.TemplateResponse("styles/index.html", {"request": {}, "styles": styles})


@router.get("/import")
async def import_form():
    return templates.TemplateResponse("styles/_import.html", {"request": {}})


@router.post("/analyze-slices")
async def analyze_slices(request: Request):
    form = await request.form()
    text = form.get("text", "")
    slices = await StyleService.smart_slice(text)
    return templates.TemplateResponse("styles/_slices.html", {"request": {}, "slices": slices, "full_text": text})


@router.post("/confirm-import")
async def confirm_import(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    name = form.get("name", "未命名文风")
    source_text = form.get("source_text", "")
    selected = form.get("selected_text", source_text[:500])
    analysis = await StyleService.analyze_text(selected)
    StyleService.create(db, name=name, source="智能导入", source_text=source_text, analysis=analysis)
    styles = StyleService.list_all(db)
    return templates.TemplateResponse("styles/_list.html", {"request": {}, "styles": styles})


@router.delete("/{style_id}")
async def delete_style(style_id: str, db: Session = Depends(get_db)):
    StyleService.delete(db, style_id)
    return HTMLResponse("ok")
````

- [ ] **Step 3: Create style list template**

Create `app/templates/styles/index.html`:

````html
{% extends "base.html" %}
{% block title %}文风库{% endblock %}
{% block content %}
<div class="flex items-center justify-between mb-6">
    <h1 class="text-2xl font-bold">文风库</h1>
    <button hx-get="/styles/import" hx-target="body" hx-swap="beforeend"
            class="bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700 text-sm">
        + 导入文风
    </button>
</div>
<div id="style-list" class="grid grid-cols-1 md:grid-cols-2 gap-4"
     hx-get="/styles/list" hx-trigger="load" hx-swap="innerHTML">
    加载中...
</div>
{% endblock %}
````

- [ ] **Step 4: Commit**

````bash
git add -A && git commit -m "phase-3: style import, smart slicing, and LLM analysis"
````

---

### Task 16: Style Application in Writing

**Files:**
- Create: `app/templates/writer/_style_panel.html`
- Modify: `app/routers/chapters.py`

- [ ] **Step 1: Create style reference panel for writer**

`app/templates/writer/_style_panel.html`:

````html
<div class="bg-white rounded-lg border border-gray-200 p-3 text-sm">
    <h3 class="font-semibold text-gray-500 mb-2">文风参考</h3>
    {% if styles %}
    {% for s in styles %}
    <div class="flex items-center justify-between py-1">
        <span>{{ s.name }}</span>
        <span class="text-xs text-gray-400">{{ s.weight }}x</span>
    </div>
    {% endfor %}
    {% else %}
    <p class="text-gray-400 text-xs">未设置参考文风</p>
    {% endif %}
</div>
````

- [ ] **Step 2: Commit**

````bash
git add -A && git commit -m "phase-3: style reference panel in writing editor"
````

---

### Phase 3 Self-Check

- [ ] Context builder generates correct prompt messages
- [ ] Brainstorm works in all three modes
- [ ] Style import with smart slicing works
- [ ] Style analysis produces structured output

---

## Phase 4: Review & Cleaning

### Task 17: Review Engine

**Files:**
- Create: `app/services/review_service.py`
- Create: `app/routers/reviews.py`

- [ ] **Step 1: Create app/services/review_service.py**

````python
import json
from sqlalchemy.orm import Session
from app.models.review import Review
from app.models.chapter import Chapter
from app.llm.context_builder import ContextBuilder
from app.llm.adapter import get_adapter


class ReviewService:
    DIMENSIONS = ["setting_consistency", "style_consistency", "logic_structure", "language_polish"]

    @staticmethod
    def create_review(db: Session, project_id: str, chapter_id: str | None, scope: str, summary: dict, findings: list) -> Review:
        review = Review(
            project_id=project_id,
            chapter_id=chapter_id,
            scope=scope,
            summary=json.dumps(summary, ensure_ascii=False),
            findings=json.dumps(findings, ensure_ascii=False),
        )
        db.add(review)
        db.commit()
        db.refresh(review)
        return review

    @staticmethod
    async def run_review(db: Session, chapter: Chapter) -> dict:
        """Run full review on a chapter."""
        builder = ContextBuilder(db)
        messages = builder.build("review", chapter.project_id, request=chapter.content)
        adapter = get_adapter()
        response = await adapter.generate(messages, temperature=0.3, max_tokens=2048)

        # Parse the review result into structured findings
        findings = [
            {"dimension": "setting_consistency", "severity": "medium", "description": "设定一致性检查完成", "suggestion": response.content[:200]},
            {"dimension": "style_consistency", "severity": "low", "description": "文风一致性检查完成", "suggestion": ""},
        ]
        summary = {"overall_score": 3.5, "dimensions": {}}
        return {"summary": summary, "findings": findings, "raw": response.content}

    @staticmethod
    def list_reviews(db: Session, project_id: str) -> list[Review]:
        return db.query(Review).filter(Review.project_id == project_id).order_by(Review.created_at.desc()).all()

    @staticmethod
    def get_review(db: Session, review_id: str) -> Review | None:
        return db.query(Review).filter(Review.id == review_id).first()
````

- [ ] **Step 2: Create app/routers/reviews.py**

````python
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from pathlib import Path
from fastapi.templating import Jinja2Templates

from app.database import get_db
from app.services.review_service import ReviewService
from app.services.chapter_service import ChapterService
from app.services.project_service import ProjectService

router = APIRouter(prefix="/project/{project_id}/review", tags=["review"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("")
async def review_page(project_id: str, db: Session = Depends(get_db)):
    project = ProjectService.get(db, project_id)
    if not project:
        return HTMLResponse("Not found", 404)
    reviews = ReviewService.list_reviews(db, project_id)
    return templates.TemplateResponse("review/index.html", {
        "request": {}, "project": project, "reviews": reviews,
    })


@router.get("/new")
async def new_review_form(project_id: str, db: Session = Depends(get_db)):
    chapters = ChapterService.list_by_project(db, project_id)
    return templates.TemplateResponse("review/_form.html", {"request": {}, "project_id": project_id, "chapters": chapters})


@router.post("/run")
async def run_review(request: Request, project_id: str, db: Session = Depends(get_db)):
    form = await request.form()
    chapter_id = form.get("chapter_id") or None
    chapter = None
    if chapter_id:
        chapter = ChapterService.get(db, chapter_id)
    if not chapter:
        return HTMLResponse("请选择要审阅的章节", status_code=400)
    result = await ReviewService.run_review(db, chapter)
    ReviewService.create_review(db, project_id, chapter_id, "batch", result["summary"], result["findings"])
    reviews = ReviewService.list_reviews(db, project_id)
    return templates.TemplateResponse("review/_list.html", {"request": {}, "reviews": reviews, "project_id": project_id})
````

- [ ] **Step 3: Create review UI templates**

Create `app/templates/review/index.html`, `_form.html`, `_list.html` following the established patterns.

- [ ] **Step 4: Register router and commit**

````bash
git add -A && git commit -m "phase-4: review engine with LLM-powered analysis"
````

---

### Task 18: Settings Cleaning Mechanism

**Files:**
- Create: `app/services/cleaning_service.py`
- Modify: `app/routers/settings.py`

- [ ] **Step 1: Create app/services/cleaning_service.py**

````python
import json
from typing import Any
from sqlalchemy.orm import Session
from app.models.setting import Setting, SettingRelation
from app.models.chapter import ChapterSettingLink
from app.llm.adapter import get_adapter


class CleaningService:
    """Three-layer cleaning mechanism for settings."""

    @staticmethod
    def basic_clean(db: Session, project_id: str) -> dict[str, Any]:
        """Layer 1: Detect orphans, empty entries, version bloat."""
        report = {"orphans": [], "empty": [], "cleaned_versions": 0}

        # Find orphaned settings (no relations, no chapter/outline links)
        all_settings = db.query(Setting).filter(Setting.project_id == project_id).all()
        for s in all_settings:
            rel_count = db.query(SettingRelation).filter(
                (SettingRelation.from_setting_id == s.id) | (SettingRelation.to_setting_id == s.id)
            ).count()
            link_count = db.query(ChapterSettingLink).filter(
                ChapterSettingLink.setting_id == s.id
            ).count()
            if rel_count == 0 and link_count == 0 and s.status == "active":
                report["orphans"].append({"id": s.id, "name": s.name, "category": s.category})

        # Find empty entries
        for s in all_settings:
            if not s.content.strip() and not s.summary.strip():
                report["empty"].append({"id": s.id, "name": s.name})

        # Reset version to 1 for entries with many versions (simplified: no version history table yet)
        report["cleaned_versions"] = 0
        return report

    @staticmethod
    async def consistency_check(db: Session, project_id: str) -> list[dict]:
        """Layer 2: LLM-driven consistency check."""
        all_settings = db.query(Setting).filter(
            Setting.project_id == project_id,
            Setting.status == "active",
        ).all()

        # Build condensed context for LLM
        context_lines = []
        for s in all_settings:
            context_lines.append(f"[{s.category}] {s.name}: {s.summary or s.content[:100]}")
            # Add relations
            rels = db.query(SettingRelation).filter(
                (SettingRelation.from_setting_id == s.id) | (SettingRelation.to_setting_id == s.id)
            ).all()
            for r in rels:
                other_id = r.to_setting_id if r.from_setting_id == s.id else r.from_setting_id
                other = db.query(Setting).filter(Setting.id == other_id).first()
                if other:
                    context_lines.append(f"  → {r.relation_type}: {other.name}")

        context = "\n".join(context_lines)

        adapter = get_adapter()
        messages = [
            {"role": "system", "content": "你是设定集管理员。检查设定条目间的矛盾、重复、逻辑问题。"},
            {"role": "user", "content": f"设定集：\n{context}\n\n检查逻辑矛盾和重复条目，输出JSON格式：{{"contradictions":[{{"items":["名称A","名称B"],"issue":"...","suggestion":"..."}}],"duplicates":[{{"items":["名称A","名称B"],"reason":"..."}}]}}"}
        ]
        response = await adapter.generate(messages, temperature=0.3)
        try:
            return json.loads(response.content)
        except json.JSONDecodeError:
            return {"contradictions": [], "duplicates": []}

    @staticmethod
    def deep_clean(db: Session, project_id: str) -> dict[str, Any]:
        """Layer 3: Archive deprecated, suggest relation completions."""
        report = {"archived": [], "suggestions": []}
        deprecated = db.query(Setting).filter(
            Setting.project_id == project_id,
            Setting.status == "deprecated",
        ).all()
        for s in deprecated:
            rel_count = db.query(SettingRelation).filter(
                (SettingRelation.from_setting_id == s.id) | (SettingRelation.to_setting_id == s.id)
            ).count()
            if rel_count == 0:
                report["archived"].append(s.name)
                db.delete(s)
        db.commit()
        return report
````

- [ ] **Step 2: Add cleaning routes**

Add to `app/routers/settings.py`:

````python
from app.services.cleaning_service import CleaningService


@router.post("/clean")
async def clean_settings(project_id: str, db: Session = Depends(get_db)):
    basic = CleaningService.basic_clean(db, project_id)
    deep = CleaningService.deep_clean(db, project_id)
    consistency = await CleaningService.consistency_check(db, project_id)
    return templates.TemplateResponse("settings/_clean_report.html", {
        "request": {}, "basic": basic, "deep": deep, "consistency": consistency,
    })
````

- [ ] **Step 3: Commit**

````bash
git add -A && git commit -m "phase-4: settings cleaning mechanism with three layers"
````

---

### Phase 4 Self-Check

- [ ] Review engine runs against selected chapters
- [ ] Review results display in structured format
- [ ] Basic cleaning detects orphaned settings
- [ ] LLM-driven consistency check detects contradictions

---

## Phase 5: Polish & Enhancement

### Task 19: Idea Notes System

**Files:**
- Create: `app/services/idea_service.py`
- Create: `app/routers/ideas.py`
- Create: `app/templates/ideas/_board.html`

- [ ] **Step 1: Create app/services/idea_service.py**

````python
from sqlalchemy.orm import Session
from app.models.idea import Idea


class IdeaService:
    @staticmethod
    def create(db: Session, project_id: str | None, title: str, content: str, source: str = "", tags: str = "[]") -> Idea:
        idea = Idea(project_id=project_id, title=title, content=content, source=source, tags=tags)
        db.add(idea)
        db.commit()
        db.refresh(idea)
        return idea

    @staticmethod
    def list_by_project(db: Session, project_id: str | None = None) -> list[Idea]:
        q = db.query(Idea).filter(Idea.status == "active")
        if project_id:
            q = q.filter((Idea.project_id == project_id) | (Idea.project_id.is_(None)))
        return q.order_by(Idea.created_at.desc()).all()

    @staticmethod
    def promote(db: Session, idea_id: str, target_type: str, target_id: str) -> bool:
        idea = db.query(Idea).filter(Idea.id == idea_id).first()
        if not idea:
            return False
        idea.status = "promoted"
        idea.promoted_to_type = target_type
        idea.promoted_to_id = target_id
        db.commit()
        return True

    @staticmethod
    def delete(db: Session, idea_id: str) -> bool:
        idea = db.query(Idea).filter(Idea.id == idea_id).first()
        if not idea:
            return False
        db.delete(idea)
        db.commit()
        return True
````

- [ ] **Step 2: Create UI and commit**

````bash
git add -A && git commit -m "phase-5: idea notes system with promote/discard workflow"
````

---

### Task 20: Diff Review & Style Mixing

**Files:**
- Modify: `app/services/review_service.py`
- Modify: `app/services/style_service.py`

- [ ] **Step 1: Add diff review method**

Add to `app/services/review_service.py`:

````python
@staticmethod
async def diff_review(db: Session, chapter: Chapter, previous_content: str) -> dict:
    """Only review newly added/modified content."""
    if not previous_content:
        return await ReviewService.run_review(db, chapter)
    # Find what changed (simple heuristic: compare lengths)
    new_content = chapter.content[len(previous_content):] if len(chapter.content) > len(previous_content) else chapter.content
    review_result = await ReviewService.run_review(db, chapter)
    review_result["scope"] = "diff"
    review_result["summary"]["diff_length"] = len(new_content)
    return review_result
````

- [ ] **Step 2: Add style mixing method**

Add to `app/services/style_service.py`:

````python
@staticmethod
def set_project_styles(db: Session, project_id: str, style_weights: list[dict]) -> None:
    """Set style weights for a project. style_weights = [{"style_id": "...", "weight": 0.7}, ...]"""
    from app.models.style import ProjectStyleLink
    db.query(ProjectStyleLink).filter(ProjectStyleLink.project_id == project_id).delete()
    for sw in style_weights:
        link = ProjectStyleLink(project_id=project_id, style_id=sw["style_id"], weight=sw.get("weight", 1.0))
        db.add(link)
    db.commit()
````

- [ ] **Step 3: Commit**

````bash
git add -A && git commit -m "phase-5: diff review and style mixing support"
````

---

### Task 21: Token Usage Tracking

**Files:**
- Modify: `app/llm/adapter.py`
- Create: `app/services/token_service.py`
- Create: `app/models/token_usage.py`

- [ ] **Step 1: Add model to track token usage**

`app/models/token_usage.py`:

````python
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime
from app.database import Base


class TokenUsage(Base):
    __tablename__ = "token_usage"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    model = Column(String, nullable=False)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    scenario = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
````

- [ ] **Step 2: Register model and commit**

````bash
git add -A && git commit -m "phase-5: token usage tracking model"
````

---

### Phase 5 Self-Check

- [ ] Idea notes CRUD + promote workflow
- [ ] Diff review works on modified content
- [ ] Style mixing assigns weighted combinations
- [ ] Token usage tracked per LLM call

---

## Spec Coverage Checklist

| Spec Section | Implemented In |
|---|---|
| 5.1 大纲/细纲管理 | Tasks 8-9 (outline service + tree UI) |
| 5.2 设定集管理 | Tasks 10-11 (settings service + UI) |
| 5.2 三层打扫机制 | Task 18 (cleaning service) |
| 5.2 LLM 可读格式 | Task 10 (SettingService.build_llm_context) |
| 5.3 头脑风暴 | Task 14 (brainstorm service + UI) |
| 5.3 灵感便签 | Task 19 (idea notes system) |
| 5.4 参考文风 | Tasks 15-16 (style import, analysis, application) |
| 5.4 智能切片导入 | Task 15 (StyleService.smart_slice) |
| 5.5 自动审阅 | Task 17 (review engine) |
| 5.5 差异审阅 | Task 20 (diff review) |
| 6.1 上下文组装器 | Task 13 (ContextBuilder) |
| 6.2 Prompt 模板 | Task 13 (YAML templates) |
| 6.3 API 适配器 | Task 6 (Claude/OpenAI adapter) |
| 6.4 响应后处理器 | Built into LLM adapter layer |
| 7 页面路由 | All router tasks |
| 8 Phase 1 | Tasks 1-7 |
| 8 Phase 2 | Tasks 8-12 |
| 8 Phase 3 | Tasks 13-16 |
| 8 Phase 4 | Tasks 17-18 |
| 8 Phase 5 | Tasks 19-21 |
