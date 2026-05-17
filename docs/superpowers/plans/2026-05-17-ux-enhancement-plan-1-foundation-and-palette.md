# UX Enhancement Plan 1: Foundation + Command Palette

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the foundation (Alpine.js + Fuse.js + ai_call table + test infra) and the Cmd+K command palette with global keyboard shortcuts, breadcrumb navigation, recent-items tracking, and cross-entity search.

**Architecture:** Add a `/static` directory served by FastAPI; load Alpine.js (state) and Fuse.js (fuzzy search) locally. Replace `token_usage` table with richer `ai_call` table that also records prompt/response/duration. The palette is a single `_palette.html` partial included in `base.html`, driven by `palette.js` Alpine component; it talks to a new `/api/search` endpoint and a JS-side command registry. Vim-style `g X` jumps and `Cmd+K/.,;/S//` shortcuts go through one `shortcuts.js` registry.

**Tech Stack:** FastAPI, SQLAlchemy, Jinja2, HTMX (existing) + Alpine.js 3.x, Fuse.js 7.x (new). Pytest + httpx for backend tests; manual UX verification for frontend.

**Reference spec:** `docs/superpowers/specs/2026-05-17-ux-enhancement-design.md`

---

## File Structure

**New files:**
- `tests/__init__.py` — empty marker
- `tests/conftest.py` — pytest fixtures (in-memory SQLite, FastAPI TestClient)
- `tests/test_ai_call_model.py` — AICall ORM tests
- `tests/test_search_service.py` — search_service tests
- `tests/test_search_router.py` — `/api/search` integration tests
- `app/models/ai_call.py` — `AICall` SQLAlchemy model
- `app/services/search_service.py` — cross-entity search logic
- `app/routers/search.py` — `/api/search` endpoint
- `app/static/js/lib/alpine.min.js` — Alpine.js 3.x (~17KB minified)
- `app/static/js/lib/fuse.min.js` — Fuse.js 7.x (~14KB minified)
- `app/static/js/palette.js` — Alpine component for command palette
- `app/static/js/palette-commands.js` — hard-coded command registry
- `app/static/js/shortcuts.js` — global keyboard shortcut registry
- `app/static/js/recent-items.js` — localStorage helper for recent visits
- `app/static/css/enhancements.css` — new component styles
- `app/templates/_palette.html` — palette HTML included in base.html
- `app/templates/_shortcuts_help.html` — `Cmd+/` help modal
- `app/templates/_breadcrumb.html` — breadcrumb partial
- `app/migrations/__init__.py` — empty marker
- `app/migrations/m001_token_usage_to_ai_call.py` — one-time data migration

**Modified files:**
- `pyproject.toml` — add `pytest`, `pytest-asyncio`, `httpx` (already present)
- `app/main.py` — mount `/static`, call migration on startup
- `app/database.py` — register `ai_call` model, deregister `token_usage`
- `app/models/__init__.py` — export `AICall`, drop `TokenUsage`
- `app/llm/adapter.py` — `record_usage` writes to `ai_call`
- `app/templates/base.html` — load Alpine/Fuse/enhancements; include `_palette.html`, `_shortcuts_help.html`; add `{% block breadcrumb %}`; add `⌘K` nav button
- `app/templates/project/detail.html` — fill breadcrumb block
- `app/templates/outline/index.html` — fill breadcrumb block
- `app/templates/writer/index.html` — fill breadcrumb block; record recent-item on mount
- `app/templates/settings/index.html` — fill breadcrumb block
- `app/templates/review/index.html` — fill breadcrumb block

**Deleted files:**
- `app/models/token_usage.py` — after migration completes (Task 7)

---

## Task 1: Test Infrastructure

**Files:**
- Modify: `pyproject.toml`
- Create: `tests/__init__.py`, `tests/conftest.py`, `tests/test_smoke.py`

- [ ] **Step 1: Add test dependencies to pyproject.toml**

Append to the `dependencies` list in `pyproject.toml`:

```toml
[project.optional-dependencies]
test = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
]
```

- [ ] **Step 2: Install test deps**

Run: `pip install -e ".[test]"`
Expected: pytest and pytest-asyncio installed without errors.

- [ ] **Step 3: Create empty marker for tests package**

Create `tests/__init__.py` with no content.

- [ ] **Step 4: Create conftest.py with in-memory DB fixture**

Create `tests/conftest.py`:

```python
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.database import Base, get_db
from app.main import app


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionTesting = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionTesting()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
```

- [ ] **Step 5: Create smoke test to verify pytest works**

Create `tests/test_smoke.py`:

```python
def test_pytest_runs():
    assert 1 + 1 == 2


def test_app_imports(client):
    response = client.get("/")
    assert response.status_code == 200
```

- [ ] **Step 6: Run smoke test**

Run: `pytest tests/test_smoke.py -v`
Expected: 2 passed.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml tests/
git commit -m "test: bootstrap pytest with in-memory SQLite fixtures"
```

---

## Task 2: Static File Mount

**Files:**
- Modify: `app/main.py`
- Create: `app/static/.gitkeep`, `app/static/js/.gitkeep`, `app/static/js/lib/.gitkeep`, `app/static/css/.gitkeep`

- [ ] **Step 1: Create empty static directories**

```bash
mkdir -p app/static/js/lib app/static/css
touch app/static/js/lib/.gitkeep app/static/css/.gitkeep
```

- [ ] **Step 2: Mount /static in main.py**

In `app/main.py`, after the existing `app = FastAPI(...)` and before the router includes, add:

```python
from fastapi.staticfiles import StaticFiles
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
```

Note: `BASE_DIR` is already defined later in the file as `Path(__file__).parent`. Move the `BASE_DIR = Path(__file__).parent` line above the `app.mount(...)` line.

Final order:

```python
app = FastAPI(title="AI Novel Generation Tool")
BASE_DIR = Path(__file__).parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.include_router(projects.router)
# ... other routers
```

- [ ] **Step 3: Add smoke test for static mount**

Add to `tests/test_smoke.py`:

```python
def test_static_mount_exists(client):
    # 404 is fine — we just want to confirm /static/ is registered (not 405 Method Not Allowed)
    response = client.get("/static/nonexistent.js")
    assert response.status_code == 404
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_smoke.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add app/main.py app/static/
git commit -m "feat: mount /static directory for frontend assets"
```

---

## Task 3: Vendor Alpine.js and Fuse.js

**Files:**
- Create: `app/static/js/lib/alpine.min.js`, `app/static/js/lib/fuse.min.js`

- [ ] **Step 1: Download Alpine.js 3.x**

Run:

```bash
curl -sSL -o app/static/js/lib/alpine.min.js https://cdn.jsdelivr.net/npm/alpinejs@3.13.10/dist/cdn.min.js
```

Expected: file `app/static/js/lib/alpine.min.js` exists, size > 30KB.

- [ ] **Step 2: Download Fuse.js 7.x**

Run:

```bash
curl -sSL -o app/static/js/lib/fuse.min.js https://cdn.jsdelivr.net/npm/fuse.js@7.0.0/dist/fuse.min.js
```

Expected: file `app/static/js/lib/fuse.min.js` exists, size > 10KB.

- [ ] **Step 3: Verify files load via running server**

Run the dev server in another shell:

```bash
uvicorn app.main:app --reload --port 8000
```

Then in this shell:

```bash
curl -sI http://localhost:8000/static/js/lib/alpine.min.js | head -1
curl -sI http://localhost:8000/static/js/lib/fuse.min.js | head -1
```

Expected: both return `HTTP/1.1 200 OK`.

Stop the dev server.

- [ ] **Step 4: Commit**

```bash
git add app/static/js/lib/
git commit -m "chore: vendor Alpine.js 3.13 and Fuse.js 7.0"
```

---

## Task 4: AICall Model

**Files:**
- Create: `app/models/ai_call.py`, `tests/test_ai_call_model.py`
- Modify: `app/database.py`, `app/models/__init__.py`

- [ ] **Step 1: Write failing test for AICall model**

Create `tests/test_ai_call_model.py`:

```python
from datetime import datetime
from app.models.ai_call import AICall


def test_ai_call_insert_with_minimum_fields(db_session):
    call = AICall(
        scenario="writing",
        model="claude-sonnet-4-6",
        input_tokens=100,
        output_tokens=50,
        status="success",
    )
    db_session.add(call)
    db_session.commit()
    db_session.refresh(call)
    assert call.id is not None
    assert call.scenario == "writing"
    assert call.input_tokens == 100
    assert call.output_tokens == 50
    assert call.status == "success"
    assert isinstance(call.created_at, datetime)


def test_ai_call_with_prompt_response_and_duration(db_session):
    call = AICall(
        scenario="outline_gen",
        model="claude-sonnet-4-6",
        prompt="Write a chapter outline",
        response="Chapter 1: ...",
        input_tokens=200,
        output_tokens=300,
        duration_ms=4500,
        status="success",
        project_id="proj-123",
    )
    db_session.add(call)
    db_session.commit()
    db_session.refresh(call)
    assert call.prompt == "Write a chapter outline"
    assert call.duration_ms == 4500
    assert call.project_id == "proj-123"


def test_ai_call_error_status(db_session):
    call = AICall(
        scenario="review",
        model="gpt-4-turbo",
        status="error",
        error_message="rate limit",
        input_tokens=0,
        output_tokens=0,
    )
    db_session.add(call)
    db_session.commit()
    db_session.refresh(call)
    assert call.status == "error"
    assert call.error_message == "rate limit"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ai_call_model.py -v`
Expected: FAIL — `ModuleNotFoundError: app.models.ai_call`.

- [ ] **Step 3: Create the AICall model**

Create `app/models/ai_call.py`:

```python
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Index
from app.database import Base


class AICall(Base):
    __tablename__ = "ai_call"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=True)
    scenario = Column(String, nullable=False)
    model = Column(String, nullable=False)
    prompt = Column(Text, default="")
    response = Column(Text, default="")
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    duration_ms = Column(Integer, nullable=True)
    status = Column(String, default="success")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


Index("ai_call_created_idx", AICall.created_at.desc())
Index("ai_call_scenario_idx", AICall.scenario)
Index("ai_call_project_idx", AICall.project_id)
```

- [ ] **Step 4: Register model in database.py and models/__init__.py**

In `app/database.py`, replace the `init_db()` body to add `ai_call`:

```python
def init_db():
    """Import all models so Base has them registered, then create tables."""
    from app.models import project, outline, setting, chapter, style, review, idea, token_usage, ai_call  # noqa
    Base.metadata.create_all(bind=engine)
```

In `app/models/__init__.py`, add after the TokenUsage import:

```python
from app.models.ai_call import AICall
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_ai_call_model.py -v`
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add app/models/ai_call.py app/database.py app/models/__init__.py tests/test_ai_call_model.py
git commit -m "feat: add AICall model with prompt/response/duration tracking"
```

---

## Task 5: Migrate token_usage Data to ai_call

**Files:**
- Create: `app/migrations/__init__.py`, `app/migrations/m001_token_usage_to_ai_call.py`
- Modify: `app/main.py`

- [ ] **Step 1: Create migrations package marker**

Create `app/migrations/__init__.py` with content:

```python
"""One-time data migrations run on startup."""
```

- [ ] **Step 2: Write the migration**

Create `app/migrations/m001_token_usage_to_ai_call.py`:

```python
"""Migrate rows from token_usage to ai_call.

Idempotent: checks for an existing marker column to avoid re-running.
"""
from sqlalchemy import text


MIGRATION_KEY = "m001_token_usage_to_ai_call"


def run(engine):
    with engine.begin() as conn:
        # Skip if token_usage no longer exists (already migrated or never existed)
        inspector_result = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='token_usage'"
        )).fetchone()
        if not inspector_result:
            return

        # Skip if migration already ran (check a sentinel row by id)
        already = conn.execute(text(
            "SELECT id FROM ai_call WHERE id = :k"
        ), {"k": MIGRATION_KEY}).fetchone()
        if already:
            return

        # Copy rows
        rows = conn.execute(text(
            "SELECT id, model, input_tokens, output_tokens, scenario, created_at FROM token_usage"
        )).fetchall()
        for r in rows:
            conn.execute(text(
                "INSERT INTO ai_call (id, project_id, scenario, model, prompt, response, "
                "input_tokens, output_tokens, duration_ms, status, error_message, created_at) "
                "VALUES (:id, NULL, :scenario, :model, '', '', :input_tokens, :output_tokens, "
                "NULL, 'success', NULL, :created_at)"
            ), {
                "id": r.id,
                "scenario": r.scenario or "",
                "model": r.model,
                "input_tokens": r.input_tokens or 0,
                "output_tokens": r.output_tokens or 0,
                "created_at": r.created_at,
            })

        # Insert sentinel row
        conn.execute(text(
            "INSERT INTO ai_call (id, scenario, model, status, input_tokens, output_tokens) "
            "VALUES (:k, '__migration__', '__migration__', 'success', 0, 0)"
        ), {"k": MIGRATION_KEY})
```

- [ ] **Step 3: Wire migration into startup**

In `app/main.py`, modify `on_startup`:

```python
@app.on_event("startup")
def on_startup():
    os.makedirs(BASE_DIR.parent / "data", exist_ok=True)
    init_db()
    from app.migrations import m001_token_usage_to_ai_call
    from app.database import engine
    m001_token_usage_to_ai_call.run(engine)
```

- [ ] **Step 4: Test the migration**

Append to `tests/test_ai_call_model.py`:

```python
from sqlalchemy import text
from app.migrations import m001_token_usage_to_ai_call


def test_migration_copies_token_usage_rows(db_session):
    engine = db_session.get_bind()
    with engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO token_usage (id, model, input_tokens, output_tokens, scenario, created_at) "
            "VALUES ('t1', 'claude', 100, 50, 'writing', '2026-05-17 10:00:00')"
        ))

    m001_token_usage_to_ai_call.run(engine)

    with engine.connect() as conn:
        row = conn.execute(text("SELECT * FROM ai_call WHERE id='t1'")).fetchone()
        assert row is not None
        assert row.model == "claude"
        assert row.input_tokens == 100
        assert row.scenario == "writing"


def test_migration_is_idempotent(db_session):
    engine = db_session.get_bind()
    with engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO token_usage (id, model, input_tokens, output_tokens, scenario, created_at) "
            "VALUES ('t2', 'gpt', 100, 50, 'review', '2026-05-17 10:00:00')"
        ))

    m001_token_usage_to_ai_call.run(engine)
    m001_token_usage_to_ai_call.run(engine)  # second call should be a no-op

    with engine.connect() as conn:
        rows = conn.execute(text("SELECT * FROM ai_call WHERE id='t2'")).fetchall()
        assert len(rows) == 1
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_ai_call_model.py -v`
Expected: 5 passed (3 model + 2 migration).

- [ ] **Step 6: Commit**

```bash
git add app/migrations/ app/main.py tests/test_ai_call_model.py
git commit -m "feat: migrate token_usage rows to ai_call on startup"
```

---

## Task 6: Switch LLM Adapter to Write ai_call

**Files:**
- Modify: `app/llm/adapter.py`

- [ ] **Step 1: Add a failing test for adapter writing ai_call**

Create `tests/test_adapter_records.py`:

```python
from app.llm.adapter import record_usage
from app.models.ai_call import AICall


def test_record_usage_writes_to_ai_call(db_session):
    record_usage(db_session, model="claude-sonnet-4-6",
                 usage={"input_tokens": 120, "output_tokens": 80},
                 scenario="writing")
    records = db_session.query(AICall).all()
    assert len(records) == 1
    assert records[0].model == "claude-sonnet-4-6"
    assert records[0].input_tokens == 120
    assert records[0].output_tokens == 80
    assert records[0].scenario == "writing"
    assert records[0].status == "success"


def test_record_usage_supports_prompt_response_duration(db_session):
    record_usage(
        db_session,
        model="gpt-4-turbo",
        usage={"input_tokens": 50, "output_tokens": 30},
        scenario="brainstorm",
        prompt="hello",
        response="world",
        duration_ms=2100,
        project_id="proj-1",
    )
    rec = db_session.query(AICall).first()
    assert rec.prompt == "hello"
    assert rec.response == "world"
    assert rec.duration_ms == 2100
    assert rec.project_id == "proj-1"


def test_record_usage_no_op_when_empty_usage(db_session):
    record_usage(db_session, model="claude", usage={}, scenario="writing")
    assert db_session.query(AICall).count() == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_adapter_records.py -v`
Expected: FAIL — function still writes to `TokenUsage`, `AICall` count is 0.

- [ ] **Step 3: Rewrite `record_usage` to write AICall**

In `app/llm/adapter.py`, replace the existing `record_usage` function with:

```python
def record_usage(db: Any, model: str, usage: dict, scenario: str = "",
                 prompt: str = "", response: str = "", duration_ms: int | None = None,
                 project_id: str | None = None):
    """Record an AI call. No-op if usage is empty."""
    from app.models.ai_call import AICall
    if not usage:
        return
    record = AICall(
        model=model,
        input_tokens=usage.get("input_tokens", 0),
        output_tokens=usage.get("output_tokens", 0),
        scenario=scenario,
        prompt=prompt or "",
        response=response or "",
        duration_ms=duration_ms,
        status="success",
        project_id=project_id,
    )
    db.add(record)
    db.commit()
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_adapter_records.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add app/llm/adapter.py tests/test_adapter_records.py
git commit -m "refactor: record_usage writes to ai_call instead of token_usage"
```

---

## Task 7: Remove TokenUsage Model

**Files:**
- Delete: `app/models/token_usage.py`
- Modify: `app/database.py`, `app/models/__init__.py`

> Note: the `token_usage` SQL table is intentionally left in place so the idempotent migration (Task 5) keeps working for fresh clones with older snapshots. The Python model is the only thing removed.

- [ ] **Step 1: Remove TokenUsage import from app/database.py**

In `app/database.py`, change the import line to remove `token_usage`:

```python
def init_db():
    from app.models import project, outline, setting, chapter, style, review, idea, ai_call  # noqa
    Base.metadata.create_all(bind=engine)
```

- [ ] **Step 2: Remove TokenUsage export from app/models/__init__.py**

In `app/models/__init__.py`, remove the line `from app.models.token_usage import TokenUsage`.

- [ ] **Step 3: Verify nothing else imports TokenUsage**

Run: `grep -r "TokenUsage\|token_usage" app/ --include="*.py"`
Expected: only references in `app/migrations/m001_*.py` (uses raw SQL, no model import). If anything else turns up, fix it (the only spot was `app/llm/adapter.py:73` which Task 6 already replaced).

- [ ] **Step 4: Delete the model file**

Run: `rm app/models/token_usage.py`

- [ ] **Step 5: Run all tests**

Run: `pytest tests/ -v`
Expected: all pass.

- [ ] **Step 6: Manual smoke**

Run the server:

```bash
uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000`. Verify no errors in console. Then make a small change in a project (e.g., create a project), confirm the app responds. Stop server.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "refactor: drop TokenUsage Python model (table preserved for migration)"
```

---

## Task 8: Breadcrumb Partial

**Files:**
- Create: `app/templates/_breadcrumb.html`
- Modify: `app/templates/base.html`

- [ ] **Step 1: Create breadcrumb partial**

Create `app/templates/_breadcrumb.html`:

```html
{# Args: crumbs = list of {title: str, href: str|None} #}
{% if crumbs %}
<nav class="breadcrumb" aria-label="位置导航">
  {% for c in crumbs %}
    {% if c.href and not loop.last %}
      <a href="{{ c.href }}" class="breadcrumb-link">{{ c.title }}</a>
      <span class="breadcrumb-sep">›</span>
    {% else %}
      <span class="breadcrumb-current">{{ c.title }}</span>
    {% endif %}
  {% endfor %}
</nav>
{% endif %}
```

- [ ] **Step 2: Add breadcrumb block + CSS in base.html**

In `app/templates/base.html`, find the `<main class="main-content">` element. Inside, before `{% block content %}`, add the breadcrumb block:

```html
<main class="main-content">
    {% block breadcrumb %}{% endblock %}
    {% block content %}{% endblock %}
</main>
```

In the `<style>` block in `base.html`, append these breadcrumb styles before the closing `</style>`:

```css
.breadcrumb {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    font-size: 0.8125rem;
    color: var(--text-tertiary);
    margin-bottom: 1rem;
    flex-wrap: wrap;
}
.breadcrumb-link {
    color: var(--text-secondary);
    text-decoration: none;
    transition: color var(--transition);
}
.breadcrumb-link:hover {
    color: var(--accent);
}
.breadcrumb-sep {
    color: var(--text-tertiary);
    opacity: 0.6;
}
.breadcrumb-current {
    color: var(--text);
    font-weight: 500;
}
```

- [ ] **Step 3: Manual smoke**

Run server, load `/`. Confirm no rendering errors. Breadcrumb block is empty for dashboard (no crumbs defined yet).

- [ ] **Step 4: Commit**

```bash
git add app/templates/_breadcrumb.html app/templates/base.html
git commit -m "feat: breadcrumb partial and base.html block"
```

---

## Task 9: Fill Breadcrumb on Project/Outline/Writer/Settings/Review Pages

**Files:**
- Modify: `app/templates/project/detail.html`, `app/templates/outline/index.html`, `app/templates/writer/index.html`, `app/templates/settings/index.html`, `app/templates/review/index.html`, `app/templates/brainstorm/index.html`

- [ ] **Step 1: Add breadcrumb to project/detail.html**

In `app/templates/project/detail.html`, insert a new `{% block breadcrumb %}` before the existing `{% block content %}`. The `{% set crumbs %}` must live inside the breadcrumb block so it's in scope when `_breadcrumb.html` is included.

Final structure of `project/detail.html`:

```html
{% extends "base.html" %}
{% block title %}{{ project.title }} - Novel Forge{% endblock %}

{% block breadcrumb %}
  {% set crumbs = [
    {"title": "项目", "href": "/"},
    {"title": project.title, "href": none},
  ] %}
  {% include "_breadcrumb.html" %}
{% endblock %}

{% block content %}
{# ... existing content unchanged ... #}
{% endblock %}
```

- [ ] **Step 2: Add breadcrumb to outline/index.html**

Insert before `{% block content %}` (line 5 of the existing file):

```html
{% block breadcrumb %}
  {% set crumbs = [
    {"title": "项目", "href": "/"},
    {"title": project.title, "href": "/projects/" ~ project.id},
    {"title": "大纲", "href": none},
  ] %}
  {% include "_breadcrumb.html" %}
{% endblock %}
```

- [ ] **Step 3: Add breadcrumb to writer/index.html**

Insert before `{% block content %}`:

```html
{% block breadcrumb %}
  {% set crumbs = [
    {"title": "项目", "href": "/"},
    {"title": project.title, "href": "/projects/" ~ project.id},
    {"title": "写作", "href": none},
  ] %}
  {% include "_breadcrumb.html" %}
{% endblock %}
```

- [ ] **Step 4: Add breadcrumb to settings/index.html**

Insert before `{% block content %}`:

```html
{% block breadcrumb %}
  {% set crumbs = [
    {"title": "项目", "href": "/"},
    {"title": project.title, "href": "/projects/" ~ project.id},
    {"title": "设定集", "href": none},
  ] %}
  {% include "_breadcrumb.html" %}
{% endblock %}
```

- [ ] **Step 5: Add breadcrumb to review/index.html**

Insert before `{% block content %}`:

```html
{% block breadcrumb %}
  {% set crumbs = [
    {"title": "项目", "href": "/"},
    {"title": project.title, "href": "/projects/" ~ project.id},
    {"title": "审阅", "href": none},
  ] %}
  {% include "_breadcrumb.html" %}
{% endblock %}
```

- [ ] **Step 6: Add breadcrumb to brainstorm/index.html**

Insert before `{% block content %}`:

```html
{% block breadcrumb %}
  {% set crumbs = [
    {"title": "工具", "href": "/"},
    {"title": "头脑风暴", "href": none},
  ] %}
  {% include "_breadcrumb.html" %}
{% endblock %}
```

- [ ] **Step 7: Manual smoke**

Run server. Visit:
- `http://localhost:8000/projects/<some-project-id>` — see "项目 › <project title>"
- `http://localhost:8000/project/<id>/outline` — see "项目 › <title> › 大纲"
- `http://localhost:8000/project/<id>/writer` — see "项目 › <title> › 写作"
- `http://localhost:8000/project/<id>/settings` — see "项目 › <title> › 设定集"
- `http://localhost:8000/project/<id>/review` — see "项目 › <title> › 审阅"
- `http://localhost:8000/brainstorm` — see "工具 › 头脑风暴"

Stop server.

- [ ] **Step 8: Commit**

```bash
git add app/templates/
git commit -m "feat: breadcrumb on project / outline / writer / settings / review / brainstorm"
```

---

## Task 10: Cross-Entity Search Service

**Files:**
- Create: `app/services/search_service.py`, `tests/test_search_service.py`

- [ ] **Step 1: Write failing tests for search service**

Create `tests/test_search_service.py`:

```python
from app.models.project import Project
from app.models.chapter import Chapter
from app.models.outline import Outline
from app.models.setting import Setting
from app.models.idea import Idea
from app.services.search_service import SearchService


def _seed(db):
    p1 = Project(id="p1", title="时间机器", description="科幻小说")
    p2 = Project(id="p2", title="魔法学院", description="奇幻设定")
    db.add_all([p1, p2])

    db.add(Chapter(id="c1", project_id="p1", title="第一章·命名风暴", content="魔法风暴肆虐", sort_order=1))
    db.add(Chapter(id="c2", project_id="p1", title="第二章·归来", content="主角归来", sort_order=2))

    db.add(Outline(id="o1", project_id="p1", title="主线·时间循环", summary="时间循环的核心", level=1, sort_order=1))

    db.add(Setting(id="s1", project_id="p2", name="魔法风暴系", category="体系", content="一种元素系魔法", summary=""))
    db.add(Idea(id="i1", project_id="p1", title="风暴起源", content="风暴的起源应当与古代仪式有关"))

    db.commit()


def test_search_returns_chapters_by_title(db_session):
    _seed(db_session)
    results = SearchService.search(db_session, q="命名风暴", type="all")
    assert any(r["id"] == "c1" and r["type"] == "chapter" for r in results)


def test_search_filters_by_type(db_session):
    _seed(db_session)
    results = SearchService.search(db_session, q="风暴", type="setting")
    assert all(r["type"] == "setting" for r in results)
    assert any(r["id"] == "s1" for r in results)


def test_search_returns_snippet(db_session):
    _seed(db_session)
    results = SearchService.search(db_session, q="时间循环", type="outline")
    assert len(results) == 1
    assert results[0]["snippet"] != ""


def test_search_attaches_project_title(db_session):
    _seed(db_session)
    results = SearchService.search(db_session, q="时间机器", type="project")
    assert results[0]["project_title"] is None  # project IS the project
    results = SearchService.search(db_session, q="命名风暴", type="chapter")
    assert results[0]["project_title"] == "时间机器"


def test_search_idea_by_title_or_content(db_session):
    _seed(db_session)
    by_title = SearchService.search(db_session, q="风暴起源", type="idea")
    assert any(r["id"] == "i1" for r in by_title)
    by_content = SearchService.search(db_session, q="古代仪式", type="idea")
    assert any(r["id"] == "i1" for r in by_content)


def test_search_respects_limit(db_session):
    _seed(db_session)
    results = SearchService.search(db_session, q="", type="all", limit=2)
    assert len(results) <= 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_search_service.py -v`
Expected: FAIL — `app.services.search_service` doesn't exist.

- [ ] **Step 3: Implement SearchService**

Create `app/services/search_service.py`:

```python
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.chapter import Chapter
from app.models.outline import Outline
from app.models.setting import Setting
from app.models.idea import Idea


def _snippet(text: str, q: str, width: int = 80) -> str:
    if not text:
        return ""
    text = str(text)
    if not q:
        return text[:width]
    lower_text = text.lower()
    idx = lower_text.find(q.lower())
    if idx < 0:
        return text[:width]
    start = max(0, idx - width // 2)
    return text[start : start + width]


class SearchService:
    @staticmethod
    def search(db: Session, q: str, type: str = "all", limit: int = 50, project_id: str | None = None) -> list[dict]:
        q = (q or "").strip()
        like = f"%{q}%" if q else "%"
        results: list[dict] = []
        project_titles: dict[str, str] = {p.id: p.title for p in db.query(Project).all()}

        type_handlers = {
            "project": SearchService._search_projects,
            "chapter": SearchService._search_chapters,
            "outline": SearchService._search_outlines,
            "setting": SearchService._search_settings,
            "idea": SearchService._search_ideas,
        }

        if type == "all":
            for handler in type_handlers.values():
                results.extend(handler(db, q, like, project_titles, project_id))
        elif type in type_handlers:
            results.extend(type_handlers[type](db, q, like, project_titles, project_id))

        return results[:limit]

    @staticmethod
    def _search_projects(db, q, like, project_titles, project_id):
        query = db.query(Project).filter(or_(Project.title.ilike(like), Project.description.ilike(like)))
        return [{
            "type": "project",
            "id": p.id,
            "title": p.title,
            "snippet": _snippet(p.description, q),
            "project_id": p.id,
            "project_title": None,
        } for p in query.all()]

    @staticmethod
    def _search_chapters(db, q, like, project_titles, project_id):
        query = db.query(Chapter).filter(or_(Chapter.title.ilike(like), Chapter.content.ilike(like)))
        if project_id:
            query = query.filter(Chapter.project_id == project_id)
        return [{
            "type": "chapter",
            "id": c.id,
            "title": c.title,
            "snippet": _snippet(c.content, q),
            "project_id": c.project_id,
            "project_title": project_titles.get(c.project_id),
        } for c in query.all()]

    @staticmethod
    def _search_outlines(db, q, like, project_titles, project_id):
        query = db.query(Outline).filter(or_(Outline.title.ilike(like), Outline.summary.ilike(like)))
        if project_id:
            query = query.filter(Outline.project_id == project_id)
        return [{
            "type": "outline",
            "id": o.id,
            "title": o.title,
            "snippet": _snippet(o.summary, q),
            "project_id": o.project_id,
            "project_title": project_titles.get(o.project_id),
        } for o in query.all()]

    @staticmethod
    def _search_settings(db, q, like, project_titles, project_id):
        # Setting uses `name`, `summary`, `content` (no `title` column)
        query = db.query(Setting).filter(or_(
            Setting.name.ilike(like),
            Setting.summary.ilike(like),
            Setting.content.ilike(like),
        ))
        if project_id:
            query = query.filter(Setting.project_id == project_id)
        return [{
            "type": "setting",
            "id": s.id,
            "title": s.name,
            "snippet": _snippet(s.summary or s.content, q),
            "project_id": s.project_id,
            "project_title": project_titles.get(s.project_id),
        } for s in query.all()]

    @staticmethod
    def _search_ideas(db, q, like, project_titles, project_id):
        # Idea has both `title` (optional) and `content`
        query = db.query(Idea).filter(or_(Idea.title.ilike(like), Idea.content.ilike(like)))
        if project_id:
            query = query.filter(Idea.project_id == project_id)
        return [{
            "type": "idea",
            "id": i.id,
            "title": i.title or (i.content or "")[:40],
            "snippet": _snippet(i.content, q),
            "project_id": i.project_id,
            "project_title": project_titles.get(i.project_id),
        } for i in query.all()]
```

> **Model field reference** (verified against `app/models/*.py`):
> - `Project`: `title`, `description`
> - `Chapter`: `title`, `content`
> - `Outline`: `title`, `summary`
> - `Setting`: `name` (not `title`), `summary`, `content`
> - `Idea`: `title` (optional), `content`

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_search_service.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add app/services/search_service.py tests/test_search_service.py
git commit -m "feat: cross-entity SearchService with snippets and type filtering"
```

---

## Task 11: /api/search Endpoint

**Files:**
- Create: `app/routers/search.py`, `tests/test_search_router.py`
- Modify: `app/main.py`

- [ ] **Step 1: Write failing integration test**

Create `tests/test_search_router.py`:

```python
from app.models.project import Project
from app.models.chapter import Chapter


def test_search_endpoint_returns_results(client, db_session):
    db_session.add(Project(id="p1", title="时间机器", description="科幻"))
    db_session.add(Chapter(id="c1", project_id="p1", title="第一章·命名风暴", content="魔法风暴", sort_order=1))
    db_session.commit()

    response = client.get("/api/search?q=命名风暴")
    assert response.status_code == 200
    body = response.json()
    assert "results" in body
    assert any(r["id"] == "c1" for r in body["results"])


def test_search_endpoint_type_filter(client, db_session):
    db_session.add(Project(id="p1", title="时间机器", description="科幻"))
    db_session.add(Chapter(id="c1", project_id="p1", title="风暴章", content="", sort_order=1))
    db_session.commit()

    response = client.get("/api/search?q=风暴&type=project")
    assert response.status_code == 200
    body = response.json()
    assert all(r["type"] == "project" for r in body["results"])


def test_search_endpoint_empty_query_returns_results(client, db_session):
    db_session.add(Project(id="p1", title="时间机器", description=""))
    db_session.commit()

    response = client.get("/api/search?q=")
    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) >= 1


def test_search_endpoint_invalid_type_returns_empty(client, db_session):
    response = client.get("/api/search?q=x&type=bogus")
    assert response.status_code == 200
    assert response.json() == {"results": [], "total": 0}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_search_router.py -v`
Expected: FAIL — 404 on `/api/search`.

- [ ] **Step 3: Implement the router**

Create `app/routers/search.py`:

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.search_service import SearchService


router = APIRouter(prefix="/api", tags=["search"])

VALID_TYPES = {"all", "project", "chapter", "outline", "setting", "idea"}


@router.get("/search")
async def search(
    q: str = Query(""),
    type: str = Query("all"),
    limit: int = Query(50, ge=1, le=200),
    project_id: str | None = Query(None),
    db: Session = Depends(get_db),
):
    if type not in VALID_TYPES:
        return {"results": [], "total": 0}
    results = SearchService.search(db, q=q, type=type, limit=limit, project_id=project_id)
    return {"results": results, "total": len(results)}
```

- [ ] **Step 4: Register the router**

In `app/main.py`, add to the imports:

```python
from app.routers import projects, outlines, settings, chapters, brainstorming, styles, reviews, ideas, config, outline_gen, search
```

And add to the `include_router` block:

```python
app.include_router(search.router)
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_search_router.py -v`
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add app/routers/search.py app/main.py tests/test_search_router.py
git commit -m "feat: /api/search endpoint for cross-entity search"
```

---

## Task 12: Global Keyboard Shortcuts Module

**Files:**
- Create: `app/static/js/shortcuts.js`, `app/templates/_shortcuts_help.html`
- Modify: `app/templates/base.html`

- [ ] **Step 1: Implement shortcuts.js**

Create `app/static/js/shortcuts.js`:

```javascript
/**
 * Global keyboard shortcut registry.
 *
 * Each entry: { keys: string, when: () => bool, do: () => void, label: string, group: string }
 * - keys: lowercase canonical form, e.g. "cmd+k", "g p", "esc"
 * - when: optional predicate; if false, the shortcut is skipped
 * - do: handler
 * - label: human description for the help modal
 * - group: section title in the help modal
 */
(function () {
    const isMac = navigator.platform.toUpperCase().includes('MAC');
    const MOD = isMac ? 'cmd' : 'ctrl';

    const shortcuts = [];

    function register(entry) {
        shortcuts.push(entry);
    }

    function isEditingTarget(el) {
        if (!el) return false;
        const tag = el.tagName;
        if (tag === 'INPUT' || tag === 'TEXTAREA') return true;
        if (el.isContentEditable) return true;
        return false;
    }

    function getKey(e) {
        const parts = [];
        if (e.metaKey || e.ctrlKey) parts.push(isMac ? 'cmd' : 'ctrl');
        if (e.shiftKey) parts.push('shift');
        if (e.altKey) parts.push('alt');
        const k = e.key.toLowerCase();
        if (k === ' ') parts.push('space');
        else if (k.length === 1) parts.push(k);
        else parts.push(k);
        return parts.join('+');
    }

    // Vim-style chord state (e.g. "g p")
    let chord = '';
    let chordTimer = null;

    function clearChord() {
        chord = '';
        if (chordTimer) { clearTimeout(chordTimer); chordTimer = null; }
        const hint = document.getElementById('chord-hint');
        if (hint) hint.style.display = 'none';
    }

    function showChordHint(prefix) {
        let hint = document.getElementById('chord-hint');
        if (!hint) {
            hint = document.createElement('div');
            hint.id = 'chord-hint';
            hint.style.cssText = 'position:fixed;bottom:4rem;left:50%;transform:translateX(-50%);background:var(--bg-card);border:1px solid var(--border);border-radius:8px;padding:0.5rem 1rem;font-family:monospace;font-size:0.875rem;box-shadow:var(--shadow-md);z-index:1000;';
            document.body.appendChild(hint);
        }
        hint.textContent = prefix + '...';
        hint.style.display = 'block';
    }

    document.addEventListener('keydown', function (e) {
        const editing = isEditingTarget(e.target);
        const key = getKey(e);

        // Always-allowed shortcuts even in inputs
        const alwaysOn = new Set([
            `${MOD}+k`, `${MOD}+s`, `${MOD}+.`, `${MOD}+;`, `${MOD}+/`, 'escape',
        ]);

        // Vim-style chord: "g" followed by another letter
        if (!editing && key === 'g' && !chord) {
            chord = 'g';
            showChordHint('g ');
            chordTimer = setTimeout(clearChord, 800);
            e.preventDefault();
            return;
        }
        if (chord === 'g' && !editing) {
            const chordKey = `g ${key}`;
            const match = shortcuts.find(s => s.keys === chordKey && (!s.when || s.when()));
            clearChord();
            if (match) { e.preventDefault(); match.do(); }
            return;
        }

        if (editing && !alwaysOn.has(key)) return;

        const match = shortcuts.find(s => s.keys === key && (!s.when || s.when()));
        if (match) {
            e.preventDefault();
            match.do();
        }
    });

    window.Shortcuts = { register, list: () => shortcuts.slice(), MOD };
})();
```

- [ ] **Step 2: Create the help modal template**

Create `app/templates/_shortcuts_help.html`:

```html
<!-- Cmd+/ shortcut help modal -->
<div id="shortcuts-help-modal" class="modal-overlay" style="display:none;" onclick="if(event.target===this)this.style.display='none'">
  <div class="modal-content" style="padding:1.5rem;max-width:520px;width:90%;">
    <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:1rem;">
      <h2 class="heading-lg" style="margin:0;">键盘快捷键</h2>
      <button onclick="document.getElementById('shortcuts-help-modal').style.display='none'" class="btn btn-ghost btn-sm">关闭</button>
    </div>
    <div id="shortcuts-help-body" style="font-size:0.875rem;">
      <!-- Populated by JS -->
    </div>
  </div>
</div>
<script>
window.openShortcutsHelp = function () {
    const body = document.getElementById('shortcuts-help-body');
    const list = window.Shortcuts.list();
    const groups = {};
    list.forEach(s => {
        if (!groups[s.group]) groups[s.group] = [];
        groups[s.group].push(s);
    });
    let html = '';
    for (const g of Object.keys(groups)) {
        html += `<div class="label" style="margin-top:1rem;">${g}</div>`;
        html += '<table style="width:100%;font-size:0.8125rem;">';
        for (const s of groups[g]) {
            const keyDisplay = s.keys.replace(/cmd\+/gi, '⌘').replace(/ctrl\+/gi, 'Ctrl+').replace(/\+/g, ' ').toUpperCase();
            html += `<tr><td style="padding:0.25rem 0;color:var(--text-secondary);">${s.label}</td><td style="text-align:right;font-family:monospace;color:var(--text);">${keyDisplay}</td></tr>`;
        }
        html += '</table>';
    }
    body.innerHTML = html;
    document.getElementById('shortcuts-help-modal').style.display = 'flex';
};
</script>
```

- [ ] **Step 3: Wire scripts into base.html**

In `app/templates/base.html`, inside the `<head>` block after the existing `<script>` tags (htmx, tailwind, marked), add:

```html
<script defer src="/static/js/lib/alpine.min.js"></script>
<script src="/static/js/lib/fuse.min.js"></script>
<script src="/static/js/shortcuts.js"></script>
```

And just before the closing `</body>` tag, include the help modal:

```html
{% include "_shortcuts_help.html" %}
```

- [ ] **Step 4: Register default shortcuts**

In `app/static/js/shortcuts.js`, after the IIFE that defines `window.Shortcuts`, append default registrations:

```javascript
// Defaults
Shortcuts.register({ keys: `${Shortcuts.MOD}+/`, group: '帮助', label: '显示快捷键帮助', do: () => window.openShortcutsHelp() });
Shortcuts.register({ keys: 'escape', group: '通用', label: '关闭模态/面板', do: () => {
    const help = document.getElementById('shortcuts-help-modal');
    if (help && help.style.display === 'flex') { help.style.display = 'none'; return; }
    const palette = document.getElementById('command-palette');
    if (palette && palette.style.display === 'flex') { palette.style.display = 'none'; return; }
}});
Shortcuts.register({ keys: `${Shortcuts.MOD}+s`, group: '写作', label: '强制立即保存', do: () => {
    document.dispatchEvent(new CustomEvent('novelforge:force-save'));
}});
Shortcuts.register({ keys: 'g p', group: '跳转', label: '跳转项目列表', do: () => window.location.href = '/' });
Shortcuts.register({ keys: 'g i', group: '跳转', label: '跳转灵感', do: () => window.location.href = '/ideas' });
Shortcuts.register({ keys: 'g b', group: '跳转', label: '跳转头脑风暴', do: () => window.location.href = '/brainstorm' });
Shortcuts.register({ keys: 'g h', group: '跳转', label: '跳转 AI 历史', do: () => window.location.href = '/ai-history' });

// Project-scoped jumps (when on a project page)
function currentProjectId() {
    const m = window.location.pathname.match(/\/projects?\/([^/]+)/);
    return m ? m[1] : null;
}
Shortcuts.register({ keys: 'g o', group: '跳转', label: '跳转当前项目大纲', when: () => !!currentProjectId(),
    do: () => window.location.href = `/project/${currentProjectId()}/outline` });
Shortcuts.register({ keys: 'g w', group: '跳转', label: '跳转当前项目写作', when: () => !!currentProjectId(),
    do: () => window.location.href = `/project/${currentProjectId()}/writer` });
Shortcuts.register({ keys: 'g s', group: '跳转', label: '跳转当前项目设定集', when: () => !!currentProjectId(),
    do: () => window.location.href = `/project/${currentProjectId()}/settings` });
Shortcuts.register({ keys: 'g r', group: '跳转', label: '跳转当前项目审阅', when: () => !!currentProjectId(),
    do: () => window.location.href = `/project/${currentProjectId()}/review` });
```

- [ ] **Step 5: Manual smoke**

Run server. Visit `/`. Press `Cmd+/` (or `Ctrl+/`). Expected: shortcut help modal appears with the registered shortcuts grouped. Press `Esc`. Expected: modal closes. Press `g` then `b`. Expected: navigates to `/brainstorm`. Stop server.

- [ ] **Step 6: Commit**

```bash
git add app/static/js/shortcuts.js app/templates/_shortcuts_help.html app/templates/base.html
git commit -m "feat: global keyboard shortcuts registry with vim-style chords and help modal"
```

---

## Task 13: Recent Items Tracker

**Files:**
- Create: `app/static/js/recent-items.js`
- Modify: `app/templates/base.html`, page templates (writer, outline, settings)

- [ ] **Step 1: Implement recent-items.js**

Create `app/static/js/recent-items.js`:

```javascript
/**
 * Track recently-visited items in localStorage.
 *
 * Storage key: novelforge-recent
 * Structure: [{type, id, title, project_id, project_title, ts}, ...] (max 20, newest first)
 */
(function () {
    const KEY = 'novelforge-recent';
    const MAX = 20;

    function load() {
        try { return JSON.parse(localStorage.getItem(KEY) || '[]'); }
        catch (e) { return []; }
    }

    function save(items) {
        localStorage.setItem(KEY, JSON.stringify(items.slice(0, MAX)));
    }

    function record(item) {
        if (!item || !item.type || !item.id) return;
        let items = load();
        items = items.filter(i => !(i.type === item.type && i.id === item.id));
        items.unshift({ ...item, ts: Date.now() });
        save(items);
    }

    function list() {
        return load();
    }

    function clear() {
        localStorage.removeItem(KEY);
    }

    window.RecentItems = { record, list, clear };
})();
```

- [ ] **Step 2: Load script in base.html**

In `app/templates/base.html`, add inside `<head>` after the shortcuts.js line:

```html
<script src="/static/js/recent-items.js"></script>
```

- [ ] **Step 3: Record recent visit on project detail page**

In `app/templates/project/detail.html`, before `{% endblock %}` of the content block, add:

```html
<script>
window.RecentItems.record({
    type: 'project',
    id: '{{ project.id }}',
    title: {{ project.title|tojson }},
    project_id: '{{ project.id }}',
    project_title: {{ project.title|tojson }},
});
</script>
```

- [ ] **Step 4: Record on outline page**

In `app/templates/outline/index.html`, before `{% endblock %}` of content, add:

```html
<script>
window.RecentItems.record({
    type: 'outline',
    id: 'project-{{ project.id }}',
    title: '{{ project.title }} · 大纲',
    project_id: '{{ project.id }}',
    project_title: {{ project.title|tojson }},
});
</script>
```

- [ ] **Step 5: Record on writer page**

In `app/templates/writer/index.html`, before `{% endblock %}`, add:

```html
<script>
window.RecentItems.record({
    type: 'writer',
    id: 'project-{{ project.id }}',
    title: '{{ project.title }} · 写作',
    project_id: '{{ project.id }}',
    project_title: {{ project.title|tojson }},
});
</script>
```

- [ ] **Step 6: Record on settings page**

In `app/templates/settings/index.html`, before `{% endblock %}`, add:

```html
<script>
window.RecentItems.record({
    type: 'settings',
    id: 'project-{{ project.id }}',
    title: '{{ project.title }} · 设定集',
    project_id: '{{ project.id }}',
    project_title: {{ project.title|tojson }},
});
</script>
```

- [ ] **Step 7: Manual smoke**

Run server. Visit several pages (a project, then its outline, then writer). Open DevTools → Application → Local Storage → `localhost:8000`. Confirm `novelforge-recent` contains the visited items in reverse chronological order. Stop server.

- [ ] **Step 8: Commit**

```bash
git add app/static/js/recent-items.js app/templates/
git commit -m "feat: track recently-visited project/outline/writer/settings pages in localStorage"
```

---

## Task 14: Command Registry

**Files:**
- Create: `app/static/js/palette-commands.js`

- [ ] **Step 1: Implement palette-commands.js**

Create `app/static/js/palette-commands.js`:

```javascript
/**
 * Built-in command registry for the command palette.
 *
 * Each entry: { id, title, group, when?: () => bool, run: () => void, shortcut?: string }
 */
(function () {
    function currentProjectId() {
        const m = window.location.pathname.match(/\/projects?\/([^/]+)/);
        return m ? m[1] : null;
    }

    const commands = [
        { id: 'goto-projects', title: '跳转项目列表', group: '导航', shortcut: 'g p',
          run: () => window.location.href = '/' },
        { id: 'goto-styles', title: '跳转文风库', group: '导航',
          run: () => window.location.href = '/styles' },
        { id: 'goto-brainstorm', title: '跳转头脑风暴', group: '导航', shortcut: 'g b',
          run: () => window.location.href = '/brainstorm' },
        { id: 'goto-ideas', title: '跳转灵感', group: '导航', shortcut: 'g i',
          run: () => window.location.href = '/ideas' },
        { id: 'goto-config', title: '跳转配置', group: '导航',
          run: () => window.location.href = '/config' },
        { id: 'project-outline', title: '当前项目 · 大纲', group: '项目', shortcut: 'g o',
          when: () => !!currentProjectId(),
          run: () => window.location.href = `/project/${currentProjectId()}/outline` },
        { id: 'project-writer', title: '当前项目 · 写作', group: '项目', shortcut: 'g w',
          when: () => !!currentProjectId(),
          run: () => window.location.href = `/project/${currentProjectId()}/writer` },
        { id: 'project-settings', title: '当前项目 · 设定集', group: '项目', shortcut: 'g s',
          when: () => !!currentProjectId(),
          run: () => window.location.href = `/project/${currentProjectId()}/settings` },
        { id: 'project-review', title: '当前项目 · 审阅', group: '项目', shortcut: 'g r',
          when: () => !!currentProjectId(),
          run: () => window.location.href = `/project/${currentProjectId()}/review` },
        { id: 'toggle-theme', title: '切换主题（明/暗）', group: '外观',
          run: () => window.toggleTheme() },
        { id: 'shortcuts-help', title: '查看快捷键帮助', group: '帮助',
          shortcut: window.Shortcuts ? `${window.Shortcuts.MOD}+/` : '⌘/',
          run: () => window.openShortcutsHelp() },
        { id: 'new-project', title: '新建项目', group: '操作',
          run: () => { window.location.href = '/'; setTimeout(() => {
              const btn = document.querySelector('[hx-get="/projects/new"]');
              if (btn) btn.click();
          }, 100); }},
    ];

    window.PaletteCommands = { all: () => commands.filter(c => !c.when || c.when()) };
})();
```

- [ ] **Step 2: Load script in base.html**

In `app/templates/base.html`, add after `recent-items.js`:

```html
<script src="/static/js/palette-commands.js"></script>
```

- [ ] **Step 3: Manual smoke**

Run server. Open DevTools console. Run `window.PaletteCommands.all()`. Expected: returns an array. On project pages, it should include `project-outline`, `project-writer`, etc. On `/`, those project-scoped ones should be filtered out. Stop server.

- [ ] **Step 4: Commit**

```bash
git add app/static/js/palette-commands.js app/templates/base.html
git commit -m "feat: built-in command registry for palette"
```

---

## Task 15: Command Palette Template and Styles

**Files:**
- Create: `app/templates/_palette.html`, `app/static/css/enhancements.css`
- Modify: `app/templates/base.html`

- [ ] **Step 1: Create the palette template**

Create `app/templates/_palette.html`:

```html
<div id="command-palette" x-data="paletteComponent()" x-show="open" x-cloak
     style="display:none;position:fixed;inset:0;z-index:200;background:rgba(0,0,0,0.35);backdrop-filter:blur(6px);align-items:flex-start;justify-content:center;padding-top:12vh;"
     @keydown.escape.window="close()"
     @click="if($event.target.id==='command-palette')close()">
  <div class="palette-card" style="width:min(640px,90vw);background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius-lg);box-shadow:var(--shadow-xl);overflow:hidden;display:flex;flex-direction:column;max-height:70vh;">
    <input type="text" x-ref="searchInput" x-model="query" @input.debounce.150ms="onQuery()" @keydown="onKey($event)"
           placeholder="🔍 搜索一切 · 输入命令..."
           style="padding:0.875rem 1rem;border:none;border-bottom:1px solid var(--border-light);background:transparent;color:var(--text);font-family:var(--font-ui);font-size:0.9375rem;outline:none;">

    <div class="palette-tabs" style="display:flex;gap:0.25rem;padding:0.5rem 0.75rem;border-bottom:1px solid var(--border-light);flex-wrap:wrap;">
      <template x-for="t in tabs" :key="t.id">
        <button @click="setActiveTab(t.id)"
                :class="activeTab===t.id ? 'palette-tab-active' : ''"
                class="palette-tab"
                style="padding:0.25rem 0.625rem;border-radius:4px;font-size:0.75rem;background:var(--bg-hover);color:var(--text-secondary);border:none;cursor:pointer;transition:all var(--transition);"
                x-text="t.label"></button>
      </template>
    </div>

    <div class="palette-results" style="flex:1;overflow-y:auto;padding:0.25rem;">
      <template x-if="!query && grouped.recent.length > 0">
        <div>
          <div class="label" style="padding:0.5rem 0.75rem 0.25rem;">最近</div>
          <template x-for="(it, idx) in grouped.recent" :key="'r'+it.type+it.id">
            <div class="palette-row" :class="idx===selectedIndex && activeGroup==='recent' ? 'palette-row-active' : ''"
                 @mouseover="selectIndex(idx, 'recent')" @click="activate(it)"
                 style="padding:0.5rem 0.75rem;border-radius:6px;cursor:pointer;display:flex;justify-content:space-between;align-items:center;font-size:0.8125rem;">
              <span><span style="opacity:0.6;" x-text="typeIcon(it.type)"></span> <span x-text="it.title"></span></span>
              <span style="font-size:0.6875rem;color:var(--text-tertiary);" x-text="relativeTime(it.ts)"></span>
            </div>
          </template>
        </div>
      </template>

      <template x-if="!query && grouped.commands.length > 0">
        <div>
          <div class="label" style="padding:0.5rem 0.75rem 0.25rem;">常用命令</div>
          <template x-for="(c, idx) in grouped.commands" :key="c.id">
            <div class="palette-row" :class="idx===selectedIndex && activeGroup==='commands' ? 'palette-row-active' : ''"
                 @mouseover="selectIndex(idx, 'commands')" @click="activate(c)"
                 style="padding:0.5rem 0.75rem;border-radius:6px;cursor:pointer;display:flex;justify-content:space-between;align-items:center;font-size:0.8125rem;">
              <span>⚡ <span x-text="c.title"></span></span>
              <span style="font-family:monospace;font-size:0.7rem;color:var(--text-tertiary);" x-text="c.shortcut || ''"></span>
            </div>
          </template>
        </div>
      </template>

      <template x-if="query && results.length === 0 && !loading">
        <div class="empty-state" style="padding:2rem 1rem;">
          <p class="empty-state-desc">无匹配结果</p>
        </div>
      </template>

      <template x-if="query && results.length > 0">
        <div>
          <template x-for="(r, idx) in results" :key="r.type+r.id">
            <div class="palette-row" :class="idx===selectedIndex && activeGroup==='results' ? 'palette-row-active' : ''"
                 @mouseover="selectIndex(idx, 'results')" @click="activate(r)"
                 style="padding:0.5rem 0.75rem;border-radius:6px;cursor:pointer;font-size:0.8125rem;">
              <div style="display:flex;justify-content:space-between;align-items:baseline;">
                <span><span style="opacity:0.6;" x-text="typeIcon(r.type)"></span> <span x-text="r.title"></span></span>
                <span style="font-size:0.6875rem;color:var(--text-tertiary);" x-text="r.project_title || ''"></span>
              </div>
              <div x-show="r.snippet" style="font-size:0.75rem;color:var(--text-secondary);margin-top:0.125rem;" x-text="r.snippet"></div>
            </div>
          </template>
        </div>
      </template>

      <template x-if="loading">
        <div class="empty-state" style="padding:1.5rem 1rem;">
          <p class="empty-state-desc">搜索中...</p>
        </div>
      </template>
    </div>

    <div style="padding:0.5rem 0.875rem;border-top:1px solid var(--border-light);font-size:0.6875rem;color:var(--text-tertiary);display:flex;gap:1rem;">
      <span>↑↓ 选择</span>
      <span>Enter 执行</span>
      <span>Tab 切换分组</span>
      <span>Esc 关闭</span>
    </div>
  </div>
</div>
```

- [ ] **Step 2: Add palette styles to enhancements.css**

Create `app/static/css/enhancements.css`:

```css
[x-cloak] { display: none !important; }

.palette-tab-active {
    background: var(--accent) !important;
    color: var(--text-on-accent) !important;
}

.palette-row {
    transition: background var(--transition);
}
.palette-row-active {
    background: var(--accent-subtle) !important;
}
.palette-row:hover {
    background: var(--bg-hover);
}
```

- [ ] **Step 3: Include in base.html**

In `app/templates/base.html`, add inside `<head>`:

```html
<link rel="stylesheet" href="/static/css/enhancements.css">
```

And before `</body>` (after the toast container, before `_shortcuts_help.html` include), add:

```html
{% include "_palette.html" %}
```

- [ ] **Step 4: Manual smoke (palette renders but inert)**

Run server. Visit `/`. Open DevTools console. Run:

```js
document.getElementById('command-palette').style.display = 'flex';
```

Expected: palette appears, but interactions don't work yet (no Alpine component defined). Close with the close X or by re-running with `none`. Stop server.

- [ ] **Step 5: Commit**

```bash
git add app/templates/_palette.html app/static/css/enhancements.css app/templates/base.html
git commit -m "feat: command palette HTML template and styles"
```

---

## Task 16: Command Palette Alpine.js Component

**Files:**
- Create: `app/static/js/palette.js`
- Modify: `app/templates/base.html`

- [ ] **Step 1: Implement palette.js**

Create `app/static/js/palette.js`:

```javascript
/**
 * Alpine.js component for the command palette.
 *
 * Open/close via window.openPalette() / Cmd+K.
 */
function paletteComponent() {
    return {
        open: false,
        query: '',
        activeTab: 'all',
        tabs: [
            { id: 'all',     label: '全部' },
            { id: 'command', label: '命令' },
            { id: 'project', label: '项目' },
            { id: 'chapter', label: '章节' },
            { id: 'outline', label: '大纲' },
            { id: 'setting', label: '设定' },
            { id: 'idea',    label: '灵感' },
        ],
        results: [],
        loading: false,
        selectedIndex: 0,
        activeGroup: 'recent', // 'recent' | 'commands' | 'results'

        init() {
            window.openPalette = () => this.openPalette();
            window.Shortcuts.register({
                keys: `${window.Shortcuts.MOD}+k`, group: '通用', label: '打开命令面板',
                do: () => this.openPalette(),
            });
        },

        get grouped() {
            const showAll = this.activeTab === 'all' || this.activeTab === 'command';
            const showRecent = this.activeTab === 'all';
            return {
                recent: showRecent ? (window.RecentItems ? window.RecentItems.list() : []).slice(0, 5) : [],
                commands: showAll ? this.filteredCommands().slice(0, 8) : [],
            };
        },

        filteredCommands() {
            const cmds = window.PaletteCommands ? window.PaletteCommands.all() : [];
            if (!this.query) return cmds;
            const fuse = new Fuse(cmds, { keys: ['title'], threshold: 0.4 });
            return fuse.search(this.query).map(r => r.item);
        },

        openPalette() {
            this.open = true;
            this.query = '';
            this.results = [];
            this.activeTab = 'all';
            this.selectedIndex = 0;
            this.activeGroup = this.grouped.recent.length > 0 ? 'recent' : 'commands';
            this.$nextTick(() => this.$refs.searchInput.focus());
        },

        close() { this.open = false; },

        setActiveTab(id) {
            this.activeTab = id;
            this.selectedIndex = 0;
            this.onQuery();
        },

        async onQuery() {
            const q = this.query.trim();
            if (!q) { this.results = []; return; }

            // Command-only tab: don't hit API
            if (this.activeTab === 'command') {
                this.results = this.filteredCommands().map(c => ({
                    type: 'command', id: c.id, title: c.title, _cmd: c,
                }));
                return;
            }

            this.loading = true;
            const type = this.activeTab === 'all' ? 'all' : this.activeTab;
            try {
                const resp = await fetch(`/api/search?q=${encodeURIComponent(q)}&type=${type}&limit=20`);
                const body = await resp.json();
                let res = body.results || [];
                // When 'all', interleave commands with API results
                if (this.activeTab === 'all') {
                    const cmdMatches = this.filteredCommands().slice(0, 5).map(c => ({
                        type: 'command', id: c.id, title: c.title, _cmd: c,
                    }));
                    res = [...cmdMatches, ...res];
                }
                this.results = res;
                this.activeGroup = 'results';
                this.selectedIndex = 0;
            } catch (e) {
                this.results = [];
                showToast('搜索失败', 'error');
            } finally {
                this.loading = false;
            }
        },

        onKey(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                const item = this.currentItem();
                if (item) this.activate(item);
            } else if (e.key === 'ArrowDown') {
                e.preventDefault();
                this.moveSelection(1);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                this.moveSelection(-1);
            } else if (e.key === 'Tab') {
                e.preventDefault();
                const idx = this.tabs.findIndex(t => t.id === this.activeTab);
                const next = e.shiftKey ? (idx - 1 + this.tabs.length) % this.tabs.length : (idx + 1) % this.tabs.length;
                this.setActiveTab(this.tabs[next].id);
            }
        },

        currentList() {
            if (this.query) return this.results;
            if (this.activeGroup === 'recent') return this.grouped.recent;
            return this.grouped.commands;
        },

        currentItem() {
            const list = this.currentList();
            return list[this.selectedIndex];
        },

        moveSelection(delta) {
            const list = this.currentList();
            if (!list.length) return;
            this.selectedIndex = (this.selectedIndex + delta + list.length) % list.length;
        },

        selectIndex(idx, group) {
            this.selectedIndex = idx;
            this.activeGroup = group;
        },

        activate(item) {
            this.close();
            if (item._cmd) { item._cmd.run(); return; }
            if (item.type === 'command') {
                const cmd = (window.PaletteCommands.all() || []).find(c => c.id === item.id);
                if (cmd) cmd.run();
                return;
            }
            // Entity navigation
            switch (item.type) {
                case 'project':   window.location.href = `/projects/${item.id}`; break;
                case 'chapter':   window.location.href = `/project/${item.project_id}/writer?chapter=${item.id}`; break;
                case 'outline':
                case 'writer':
                case 'settings':  window.location.href = `/projects/${item.project_id}`; break;
                case 'setting':   window.location.href = `/project/${item.project_id}/settings/${item.id}`; break;
                case 'idea':      window.location.href = `/ideas`; break;
            }
        },

        typeIcon(type) {
            return { project: '📚', chapter: '📖', outline: '📋', setting: '🌍', idea: '💡',
                     writer: '✍️', settings: '🌍', command: '⚡' }[type] || '·';
        },

        relativeTime(ts) {
            if (!ts) return '';
            const diff = (Date.now() - ts) / 1000;
            if (diff < 60) return '刚刚';
            if (diff < 3600) return `${Math.floor(diff/60)} 分钟前`;
            if (diff < 86400) return `${Math.floor(diff/3600)} 小时前`;
            return `${Math.floor(diff/86400)} 天前`;
        },
    };
}
```

- [ ] **Step 2: Load script in base.html**

In `app/templates/base.html`, add after the `palette-commands.js` line:

```html
<script src="/static/js/palette.js"></script>
```

- [ ] **Step 3: Manual smoke**

Run server. Visit `/`. Press `Cmd+K` (or `Ctrl+K`). Expected:
- Palette opens with focus in the input
- Empty state shows "最近" (may be empty on first run) and "常用命令"
- Type "新建" — palette filters commands and queries `/api/search`
- Press `↓` and `↑` — selection moves
- Press `Enter` on a project result — navigates to that project
- Press `Tab` — active tab cycles through `[全部, 命令, 项目, 章节, 大纲, 设定, 灵感]`
- Press `Esc` — palette closes

Stop server.

- [ ] **Step 4: Commit**

```bash
git add app/static/js/palette.js app/templates/base.html
git commit -m "feat: command palette Alpine.js component with search, commands, and recent items"
```

---

## Task 17: ⌘K Button in Nav Bar

**Files:**
- Modify: `app/templates/base.html`

- [ ] **Step 1: Add the button**

In `app/templates/base.html`, find the `<div class="nav-links">` section. Just before the `<div class="nav-divider"></div>`, add:

```html
<button type="button" onclick="window.openPalette()" class="palette-hint" title="打开命令面板">
    <span class="palette-hint-kbd">⌘K</span>
</button>
```

And add the styles inside the `<style>` block (after the theme-toggle styles):

```css
.palette-hint {
    background: transparent;
    border: 1px solid var(--border);
    color: var(--text-secondary);
    padding: 0.25rem 0.625rem;
    border-radius: var(--radius-sm);
    font-size: 0.75rem;
    cursor: pointer;
    transition: all var(--transition);
    font-family: var(--font-ui);
}
.palette-hint:hover {
    border-color: var(--accent);
    color: var(--accent);
    background: var(--accent-subtle);
}
.palette-hint-kbd {
    font-family: var(--font-mono);
    letter-spacing: 0.05em;
}
```

- [ ] **Step 2: Manual smoke**

Run server. Visit `/`. Expected: nav bar shows `⌘K` button between nav links and theme toggle. Click it — palette opens. Stop server.

- [ ] **Step 3: Commit**

```bash
git add app/templates/base.html
git commit -m "feat: nav bar shows ⌘K palette hint button"
```

---

## Task 18: Final Integration Smoke Test

**Files:**
- None (manual testing only)

- [ ] **Step 1: Full run-through**

Run server. Verify every checkpoint:

- [ ] `Cmd+K` opens palette on every main page (`/`, `/styles`, `/brainstorm`, project detail, outline, writer, settings, review)
- [ ] Palette empty state shows recent items (after visiting some) + common commands
- [ ] Type a project name — search returns project; pressing Enter navigates
- [ ] Type a chapter keyword — chapter result shows with project name and snippet
- [ ] Tab cycles through tabs; filtered results match the active tab
- [ ] `Cmd+/` opens shortcut help; lists all registered shortcuts grouped
- [ ] `Esc` closes palette or help modal
- [ ] `g p` from any page navigates to `/`
- [ ] `g b` navigates to `/brainstorm`
- [ ] `g o` (on a project page) navigates to that project's outline
- [ ] Breadcrumbs render on project detail / outline / writer / settings / review / brainstorm
- [ ] Theme toggle still works
- [ ] Existing HTMX flows (create project, save chapter, generate outline) still work
- [ ] No JavaScript console errors

Stop server.

- [ ] **Step 2: Run all tests**

Run: `pytest tests/ -v`
Expected: all tests pass.

- [ ] **Step 3: Final commit (if any tweaks made)**

```bash
git status
# If clean, no commit needed. If anything was tweaked during smoke:
git add -A
git commit -m "fix: minor adjustments from integration smoke"
```

---

## Plan Coverage Reference

| Spec section | Covered by tasks |
|---|---|
| §2.1 File organization (static, palette, breadcrumb, ai_call) | Tasks 2, 3, 8, 14-17 |
| §2.2 Dependencies (Alpine, Fuse) | Tasks 1, 3 |
| §3.2.1 Command palette (Cmd+K) | Tasks 14-17 |
| §3.2.2 Global keyboard shortcuts | Task 12 |
| §3.2.3 Recent items | Task 13 |
| §3.2.4 Breadcrumb navigation | Tasks 8, 9 |
| §3.4.1 Global search (search service + API) | Tasks 10, 11 |
| §4 AICall model + token_usage migration | Tasks 4, 5, 6, 7 |
| §5 API endpoints (`/api/search`) | Task 11 |
| §7.1 Backend unit tests | Tasks 4, 5, 6, 10, 11 |
| §7.3 Manual UX verification | Task 18 |

**Not in this plan (deferred to Plans 2-4):**
- Writing focus features (status bar, save indicator, word count, focus/typewriter) → Plan 2
- AI transparency (token dashboard, generation progress, context preview, AI history page) → Plan 3
- Data management (inline rename, bulk select, project export) → Plan 4
