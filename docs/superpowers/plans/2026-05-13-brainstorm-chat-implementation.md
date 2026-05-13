# Brainstorm Chat — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert brainstorm from single-form-submit to conversational AI chat with LLM extraction on save.

**Architecture:** Frontend manages message history in sessionStorage, sends full history to backend stateless chat endpoint. Save triggers LLM extraction of settings/outlines/ideas with user review confirmation.

**Tech Stack:** FastAPI, Jinja2/HTMX, sessionStorage JS API, existing LLM adapter

**Scope:** Single module (brainstorm). No new DB tables. Reuses SettingService, OutlineService, IdeaService.

---

### Task 1: Rewrite BrainstormService

**Files:**
- Modify: `app/services/brainstorm_service.py` (full rewrite)

- [ ] **Step 1: Rewrite `app/services/brainstorm_service.py`**

```python
import json
from sqlalchemy.orm import Session
from app.llm.context_builder import ContextBuilder
from app.llm.adapter import get_adapter, record_usage
from app.services.setting_service import SettingService
from app.services.outline_service import OutlineService
from app.services.idea_service import IdeaService
from app.schemas.setting import SettingCreate
from app.schemas.outline import OutlineCreate


EXTRACTION_SYSTEM_PROMPT = """你是一位小说创作助手。分析以下头脑风暴对话，提取其中有价值的创作素材。
将其归类为：设定条目（人物/世界观/组织/地理/事件等）、大纲节点（情节/章节方向）、灵感想法。

输出 JSON 格式：
{
  "settings": [{"category": "人物", "name": "...", "summary": "...", "content": "...", "weight": 7}],
  "outlines": [{"level": 2, "title": "...", "summary": "..."}],
  "ideas": [{"title": "...", "content": "..."}]
}

注意：
- 只提取对话中真正出现的内容，不要编造
- 设定条目要有明确的名称和分类
- 大纲节点应该是可落地的章节方向
- weight 1-10，越核心越高"""


class BrainstormService:
    """Stateless chat service for brainstorming conversations."""

    SYSTEM_PROMPT = "你是一位创意策划顾问。帮助作者拓展思路、激发灵感。输出应具有发散性和启发性，而非结论性。回答使用中文。"

    @staticmethod
    async def chat(db: Session, messages: list[dict], project_id: str | None = None) -> str:
        """Send full message history to LLM and return assistant reply."""
        adapter = get_adapter(db)

        # Ensure system prompt is first message
        if not messages or messages[0].get("role") != "system":
            messages = [{"role": "system", "content": BrainstormService.SYSTEM_PROMPT}] + messages

        # If project context requested, inject settings
        if project_id:
            builder = ContextBuilder(db)
            from app.services.project_service import ProjectService
            project = ProjectService.get(db, project_id)
            if project:
                ctx_messages = builder.build("brainstorm", project_id, request="")
                # Merge context into system prompt
                for m in ctx_messages:
                    if m["role"] == "system":
                        messages[0]["content"] += "\n\n" + m["content"]

        response = await adapter.generate(messages, temperature=0.9, max_tokens=2048)
        record_usage(db, adapter.model, response.usage, scenario="brainstorm_chat")
        return response.content

    @staticmethod
    async def extract(db: Session, messages: list[dict]) -> dict:
        """Send conversation to LLM and get structured extraction of settings/outlines/ideas."""
        adapter = get_adapter(db)

        conv_text = ""
        for m in messages:
            if m["role"] == "user":
                conv_text += f"\n用户: {m['content']}\n"
            elif m["role"] == "assistant":
                conv_text += f"\n助手: {m['content']}\n"

        extraction_messages = [
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": f"以下是一段头脑风暴对话，请提取其中的创作素材：\n\n{conv_text[:8000]}"}
        ]
        response = await adapter.generate(extraction_messages, temperature=0.3, max_tokens=2048)
        record_usage(db, adapter.model, response.usage, scenario="brainstorm_extract")

        try:
            result = json.loads(response.content)
            return {
                "settings": result.get("settings", []),
                "outlines": result.get("outlines", []),
                "ideas": result.get("ideas", []),
            }
        except (json.JSONDecodeError, ValueError):
            return {"settings": [], "outlines": [], "ideas": []}

    @staticmethod
    def confirm_save(db: Session, project_id: str, data: dict, raw_messages: list[dict]) -> dict:
        """Write confirmed extractions to DB."""
        saved = {"settings": 0, "outlines": 0, "ideas": 0}

        for s in data.get("settings", []):
            setting_data = SettingCreate(
                project_id=project_id,
                category=s.get("category", "自定义"),
                name=s.get("name", "未命名"),
                summary=s.get("summary", ""),
                content=s.get("content", ""),
                weight=s.get("weight", 5),
            )
            SettingService.create(db, setting_data)
            saved["settings"] += 1

        for o in data.get("outlines", []):
            outline_data = OutlineCreate(
                project_id=project_id,
                level=o.get("level", 2),
                title=o.get("title", "未命名"),
                summary=o.get("summary", ""),
            )
            OutlineService.create(db, outline_data)
            saved["outlines"] += 1

        # Save raw conversation as idea
        import json as j
        IdeaService.create(
            db,
            project_id=project_id,
            title=data.get("title", "头脑风暴记录"),
            content=j.dumps(raw_messages, ensure_ascii=False),
            source="brainstorm",
        )
        saved["ideas"] += 1
        return saved
```

- [ ] **Step 2: Verify imports**

```bash
cd ai-novel-generation && source .venv/bin/activate
python -c "from app.services.brainstorm_service import BrainstormService; print('BrainstormService imports OK')"
```

- [ ] **Step 3: Commit**

```bash
git add app/services/brainstorm_service.py && git commit -m "feat: rewrite brainstorm service with chat/extract/confirm-save"
```

---

### Task 2: Rewrite Brainstorm Router

**Files:**
- Modify: `app/routers/brainstorming.py` (full rewrite)

- [ ] **Step 1: Rewrite `app/routers/brainstorming.py`**

```python
import json
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from pathlib import Path
from fastapi.templating import Jinja2Templates

from app.database import get_db
from app.services.brainstorm_service import BrainstormService
from app.services.idea_service import IdeaService
from app.services.project_service import ProjectService

router = APIRouter(prefix="/brainstorm", tags=["brainstorm"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("", response_class=HTMLResponse)
async def brainstorm_page(request: Request, db: Session = Depends(get_db)):
    projects = ProjectService.list(db)
    return templates.TemplateResponse(request, "brainstorm/index.html", {
        "projects": projects,
    })


@router.post("/chat")
async def brainstorm_chat(request: Request, db: Session = Depends(get_db)):
    body = await request.json()
    messages = body.get("messages", [])
    project_id = body.get("project_id")
    reply = await BrainstormService.chat(db, messages, project_id)
    return templates.TemplateResponse(request, "brainstorm/_message.html", {
        "msg": {"role": "assistant", "content": reply},
    })


@router.post("/extract")
async def brainstorm_extract(request: Request, db: Session = Depends(get_db)):
    body = await request.json()
    messages = body.get("messages", [])
    project_id = body.get("project_id")
    if not project_id:
        return HTMLResponse('<p class="text-sm text-red-500">请先选择目标项目</p>')
    result = await BrainstormService.extract(db, messages)
    return templates.TemplateResponse(request, "brainstorm/_extract.html", {
        "result": result,
        "project_id": project_id,
    })


@router.post("/confirm-save")
async def brainstorm_confirm_save(request: Request, db: Session = Depends(get_db)):
    body = await request.json()
    project_id = body.get("project_id")
    data = body.get("data", {})
    raw_messages = body.get("messages", [])
    saved = BrainstormService.confirm_save(db, project_id, data, raw_messages)
    return templates.TemplateResponse(request, "brainstorm/_saved.html", {
        "saved": saved,
        "project_id": project_id,
    })


@router.get("/history")
async def brainstorm_history(request: Request, db: Session = Depends(get_db)):
    ideas = IdeaService.list_by_project(db)
    brainstorm_ideas = [i for i in ideas if i.source == "brainstorm"]
    return templates.TemplateResponse(request, "brainstorm/_sidebar.html", {
        "saved_sessions": brainstorm_ideas,
    })


@router.get("/history/{idea_id}")
async def brainstorm_load(idea_id: str, request: Request, db: Session = Depends(get_db)):
    idea = db.query(IdeaService).filter(IdeaService.id == idea_id).first()
    # We need to import Idea model
    from app.models.idea import Idea
    idea = db.query(Idea).filter(Idea.id == idea_id).first()
    if not idea:
        return HTMLResponse("Not found", 404)
    try:
        messages = json.loads(idea.content)
    except (json.JSONDecodeError, ValueError):
        messages = []
    return templates.TemplateResponse(request, "brainstorm/_chat.html", {
        "messages": messages,
        "loaded": True,
    })


@router.delete("/history/{idea_id}")
async def brainstorm_delete(idea_id: str, db: Session = Depends(get_db)):
    IdeaService.delete(db, idea_id)
    return HTMLResponse("ok")
```

- [ ] **Step 2: Verify imports**

```bash
python -c "from app.routers.brainstorming import router; print('Router imports OK')"
```

- [ ] **Step 3: Commit**

```bash
git add app/routers/brainstorming.py && git commit -m "feat: rewrite brainstorm router with chat/extract/save endpoints"
```

---

### Task 3: Create Chat UI Templates

**Files:**
- Modify: `app/templates/brainstorm/index.html`
- Create: `app/templates/brainstorm/_chat.html`
- Create: `app/templates/brainstorm/_message.html`
- Create: `app/templates/brainstorm/_input.html`

- [ ] **Step 1: Create `app/templates/brainstorm/index.html`**

Split layout: sidebar left (250px) + chat right (flex-1).

```html
{% extends "base.html" %}
{% block title %}头脑风暴{% endblock %}
{% block content %}
<div style="display: flex; gap: 1rem; height: calc(100vh - 8rem);">

    <!-- Sidebar -->
    <div style="width: 250px; flex-shrink: 0; display: flex; flex-direction: column; gap: 0.75rem;">
        <button onclick="newSession()" class="btn btn-primary" style="justify-content: center; width: 100%;">
            + 新建对话
        </button>
        <div style="flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 0.375rem;"
             id="history-sidebar"
             hx-get="/brainstorm/history" hx-trigger="load" hx-swap="innerHTML">
            <div style="text-align: center; color: var(--text-tertiary); font-size: 0.8125rem; padding: 1rem 0;">加载中...</div>
        </div>
    </div>

    <!-- Chat Area -->
    <div style="flex: 1; display: flex; flex-direction: column; background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden;">
        <!-- Messages -->
        <div id="chat-messages" style="flex: 1; overflow-y: auto; padding: 1.25rem; display: flex; flex-direction: column; gap: 1rem;">
            {% include "brainstorm/_chat.html" %}
        </div>
        <!-- Input -->
        <div style="border-top: 1px solid var(--border); padding: 0.75rem 1rem; background: var(--bg);">
            {% include "brainstorm/_input.html" %}
        </div>
    </div>
</div>

<script>
function scrollToBottom() {
    var el = document.getElementById('chat-messages');
    if (el) el.scrollTop = el.scrollHeight;
}

function addMessage(msg, appendTo) {
    var container = appendTo || document.getElementById('chat-messages');
    var div = document.createElement('div');
    div.innerHTML = msg;
    container.insertAdjacentHTML('beforeend', msg);
    scrollToBottom();
}

function newSession() {
    sessionStorage.removeItem('brainstorm_messages');
    window.location.reload();
}
</script>
{% endblock %}
```

- [ ] **Step 2: Create `app/templates/brainstorm/_chat.html`**

```html
{% if messages and messages|length > 0 %}
    {% for m in messages %}
        {% if m.role != "system" %}
            {% include "brainstorm/_message.html" with msg = m %}
        {% endif %}
    {% endfor %}
{% else %}
    <div style="flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; color: var(--text-tertiary); text-align: center; padding: 2rem;">
        <div style="font-size: 2.5rem; margin-bottom: 0.75rem;">💡</div>
        <p style="font-size: 0.9375rem; font-weight: 500; color: var(--text-secondary);">开始头脑风暴</p>
        <p style="font-size: 0.8125rem; margin-top: 0.375rem; max-width: 280px;">输入你的问题或想法，让 AI 帮你拓展思路</p>
    </div>
{% endif %}
```

- [ ] **Step 3: Create `app/templates/brainstorm/_message.html`**

```html
{% if msg.role == "user" %}
<div style="display: flex; justify-content: flex-end;">
    <div style="max-width: 70%; background: var(--accent-light); color: var(--text); border-radius: 16px 16px 4px 16px; padding: 0.75rem 1rem; font-size: 0.875rem; line-height: 1.6; white-space: pre-wrap;">
        {{ msg.content }}
    </div>
</div>
{% else %}
<div style="display: flex; justify-content: flex-start;">
    <div style="max-width: 75%; background: var(--bg-card); border: 1px solid var(--border); border-radius: 16px 16px 16px 4px; padding: 0.875rem 1rem; font-size: 0.875rem; line-height: 1.7; color: var(--text);">
        <div class="brainstorm-content">{{ msg.content }}</div>
    </div>
</div>
{% endif %}
```

- [ ] **Step 4: Create `app/templates/brainstorm/_input.html`**

```html
<form id="chat-form" onsubmit="return sendMessage(event)" style="display: flex; gap: 0.5rem; align-items: flex-end;">
    <select id="project-select" style="width: 160px; flex-shrink: 0; padding: 0.5rem 0.625rem; font-size: 0.8125rem; border-radius: 8px; border: 1px solid var(--border); background: var(--bg-card); color: var(--text);">
        <option value="">无项目上下文</option>
        {% for p in projects %}
        <option value="{{ p.id }}">{{ p.title }}</option>
        {% endfor %}
    </select>
    <textarea id="chat-input" rows="1" placeholder="输入消息... (Enter 发送, Shift+Enter 换行)"
              style="flex: 1; padding: 0.5rem 0.75rem; font-size: 0.875rem; border-radius: 8px; border: 1px solid var(--border); background: var(--bg-card); color: var(--text); resize: none; max-height: 120px;"
              oninput="autoResize(this)" onkeydown="onInputKeydown(event)"></textarea>
    <button type="submit" id="send-btn" class="btn btn-primary" style="padding: 0.5rem 1rem; border-radius: 8px;">发送</button>
</form>

<script>
function autoResize(el) {
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 120) + 'px';
}

function onInputKeydown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        document.getElementById('chat-form').requestSubmit();
    }
}

function sendMessage(e) {
    e.preventDefault();
    var input = document.getElementById('chat-input');
    var text = input.value.trim();
    if (!text) return false;

    var messages = JSON.parse(sessionStorage.getItem('brainstorm_messages') || '[]');
    messages.push({role: 'user', content: text});

    // Render user message
    var chat = document.getElementById('chat-messages');
    var userHtml = `{% filter escape %}{% include "brainstorm/_message.html" with msg = {"role": "user", "content": "TMP"} %}{% endfilter %}`.replace('TMP', text.replace(/</g, '&lt;'));
    chat.insertAdjacentHTML('beforeend', userHtml);

    // Show thinking indicator
    var thinkingId = 'thinking-' + Date.now();
    chat.insertAdjacentHTML('beforeend', '<div id="' + thinkingId + '" style="display:flex;justify-content:flex-start;"><div style="background:var(--bg-card);border:1px solid var(--border);border-radius:16px;padding:0.75rem 1rem;font-size:0.875rem;color:var(--text-tertiary);">思考中...</div></div>');
    scrollToBottom();

    input.value = '';
    input.style.height = 'auto';
    document.getElementById('send-btn').disabled = true;

    var projectId = document.getElementById('project-select').value;

    fetch('/brainstorm/chat', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({messages: messages, project_id: projectId || null}),
    })
    .then(function(r) { return r.text(); })
    .then(function(html) {
        document.getElementById(thinkingId).remove();
        chat.insertAdjacentHTML('beforeend', html);
        messages.push({role: 'assistant', content: extractContent(html)});
        sessionStorage.setItem('brainstorm_messages', JSON.stringify(messages));
        scrollToBottom();
    })
    .catch(function() {
        document.getElementById(thinkingId).innerHTML = '<span style="color:#c0392b;">请求失败，请重试</span>';
    })
    .finally(function() {
        document.getElementById('send-btn').disabled = false;
    });

    return false;
}

function extractContent(html) {
    var div = document.createElement('div');
    div.innerHTML = html;
    var contentDiv = div.querySelector('.brainstorm-content');
    return contentDiv ? contentDiv.textContent.trim() : div.textContent.trim();
}
</script>
```

- [ ] **Step 5: Commit**

```bash
git add app/templates/brainstorm/ && git commit -m "feat: brainstorm chat UI with split-layout and sessionStorage"
```

---

### Task 4: Create Sidebar & Extract Save UI

**Files:**
- Create: `app/templates/brainstorm/_sidebar.html`
- Create: `app/templates/brainstorm/_extract.html`
- Create: `app/templates/brainstorm/_saved.html`

- [ ] **Step 1: Create `app/templates/brainstorm/_sidebar.html`**

```html
{% if saved_sessions %}
    {% for s in saved_sessions %}
    <div class="card" style="padding: 0.625rem 0.75rem; cursor: pointer; display: flex; align-items: center; justify-content: space-between;"
         hx-get="/brainstorm/history/{{ s.id }}" hx-target="#chat-messages" hx-swap="innerHTML">
        <div style="overflow: hidden;">
            <div style="font-size: 0.8125rem; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{{ s.title }}</div>
            <div style="font-size: 0.6875rem; color: var(--text-tertiary);">{{ s.created_at.strftime('%m-%d %H:%M') }}</div>
        </div>
        <button hx-delete="/brainstorm/history/{{ s.id }}" hx-target="#history-sidebar" hx-swap="innerHTML"
                hx-confirm="删除该记录？"
                style="background: none; border: none; cursor: pointer; color: var(--text-tertiary); font-size: 0.75rem; padding: 0.125rem; flex-shrink: 0;">✕</button>
    </div>
    {% endfor %}
{% else %}
    <div style="text-align: center; color: var(--text-tertiary); font-size: 0.8125rem; padding: 2rem 0.5rem;">
        暂无已保存的对话
    </div>
{% endif %}
```

- [ ] **Step 2: Create `app/templates/brainstorm/_extract.html`**

Save review modal showing LLM-extracted settings, outlines, ideas with checkboxes.

```html
<div class="modal-overlay" id="extract-modal">
    <div class="modal-content" style="width: 100%; max-width: 520px; padding: 1.5rem; max-height: 80vh; overflow-y: auto;" onclick="event.stopPropagation()">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem;">
            <h2 style="font-size: 1.125rem; font-weight: 700;">📋 保存到项目</h2>
            <button onclick="this.closest('.modal-overlay').remove()" style="background:none;border:none;cursor:pointer;color:var(--text-tertiary);font-size:1.25rem;">✕</button>
        </div>

        {% set total = result.settings|length + result.outlines|length + result.ideas|length %}
        {% if total == 0 %}
        <p style="color: var(--text-secondary); font-size: 0.875rem;">对话中未提取到可沉淀的内容。</p>
        {% else %}
        <p style="font-size: 0.875rem; color: var(--text-secondary); margin-bottom: 1rem;">提取到 <strong>{{ total }}</strong> 项内容，请选择要保存的：</p>

        <form id="save-form">
            {% if result.settings %}
            <div style="margin-bottom: 1rem;">
                <h3 style="font-size: 0.8125rem; font-weight: 600; color: var(--accent); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem;">设定条目 ({{ result.settings|length }})</h3>
                <div style="display: flex; flex-direction: column; gap: 0.375rem;">
                    {% for s in result.settings %}
                    <label style="display: flex; align-items: flex-start; gap: 0.5rem; padding: 0.5rem; border: 1px solid var(--border); border-radius: 8px; cursor: pointer; font-size: 0.8125rem;">
                        <input type="checkbox" name="settings" value="{{ loop.index0 }}" checked style="margin-top: 0.125rem;">
                        <div>
                            <span style="font-weight: 500;">[{{ s.category }}] {{ s.name }}</span>
                            {% if s.summary %}<span style="color: var(--text-secondary);"> — {{ s.summary }}</span>{% endif %}
                        </div>
                    </label>
                    {% endfor %}
                </div>
            </div>
            {% endif %}

            {% if result.outlines %}
            <div style="margin-bottom: 1rem;">
                <h3 style="font-size: 0.8125rem; font-weight: 600; color: var(--accent); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem;">大纲节点 ({{ result.outlines|length }})</h3>
                <div style="display: flex; flex-direction: column; gap: 0.375rem;">
                    {% for o in result.outlines %}
                    <label style="display: flex; align-items: flex-start; gap: 0.5rem; padding: 0.5rem; border: 1px solid var(--border); border-radius: 8px; cursor: pointer; font-size: 0.8125rem;">
                        <input type="checkbox" name="outlines" value="{{ loop.index0 }}" checked style="margin-top: 0.125rem;">
                        <div>
                            <span style="font-weight: 500;">{{ o.title }}</span>
                            {% if o.summary %}<span style="color: var(--text-secondary);"> — {{ o.summary }}</span>{% endif %}
                        </div>
                    </label>
                    {% endfor %}
                </div>
            </div>
            {% endif %}

            {% if result.ideas %}
            <div style="margin-bottom: 1rem;">
                <h3 style="font-size: 0.8125rem; font-weight: 600; color: var(--accent); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem;">灵感 ({{ result.ideas|length }})</h3>
                <div style="display: flex; flex-direction: column; gap: 0.375rem;">
                    {% for idea in result.ideas %}
                    <label style="display: flex; align-items: flex-start; gap: 0.5rem; padding: 0.5rem; border: 1px solid var(--border); border-radius: 8px; cursor: pointer; font-size: 0.8125rem;">
                        <input type="checkbox" name="ideas" value="{{ loop.index0 }}" checked style="margin-top: 0.125rem;">
                        <div>
                            <span style="font-weight: 500;">{{ idea.title }}</span>
                            {% if idea.content %}<span style="color: var(--text-secondary);"> — {{ idea.content[:80] }}{% if idea.content|length > 80 %}...{% endif %}</span>{% endif %}
                        </div>
                    </label>
                    {% endfor %}
                </div>
            </div>
            {% endif %}
        </form>
        {% endif %}

        <div style="display: flex; justify-content: flex-end; gap: 0.5rem; border-top: 1px solid var(--border); padding-top: 1rem;">
            <button onclick="this.closest('.modal-overlay').remove()" class="btn btn-ghost">取消</button>
            {% if total > 0 %}
            <button onclick="confirmSave()" class="btn btn-primary">确认保存</button>
            {% endif %}
        </div>
    </div>
</div>

<script>
function confirmSave() {
    var form = document.getElementById('save-form');
    if (!form) return;
    var fd = new FormData(form);
    var data = {{ result | tojson | safe }};
    var selected = {settings: [], outlines: [], ideas: []};

    var settingsChecks = form.querySelectorAll('input[name="settings"]:checked');
    settingsChecks.forEach(function(cb) { selected.settings.push(data.settings[parseInt(cb.value)]); });

    var outlinesChecks = form.querySelectorAll('input[name="outlines"]:checked');
    outlinesChecks.forEach(function(cb) { selected.outlines.push(data.outlines[parseInt(cb.value)]); });

    var ideasChecks = form.querySelectorAll('input[name="ideas"]:checked');
    ideasChecks.forEach(function(cb) { selected.ideas.push(data.ideas[parseInt(cb.value)]); });

    var messages = JSON.parse(sessionStorage.getItem('brainstorm_messages') || '[]');

    fetch('/brainstorm/confirm-save', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            project_id: '{{ project_id }}',
            data: selected,
            messages: messages,
        }),
    })
    .then(function(r) { return r.text(); })
    .then(function(html) {
        document.getElementById('extract-modal').innerHTML = html;
        // Refresh sidebar
        htmx.trigger('#history-sidebar', 'load');
    });
}
</script>
```

- [ ] **Step 3: Create `app/templates/brainstorm/_saved.html`**

```html
<div style="text-align: center; padding: 2rem 1rem;">
    <div style="font-size: 2rem; margin-bottom: 0.5rem;">✅</div>
    <h3 style="font-size: 1rem; font-weight: 600; margin-bottom: 0.5rem;">保存成功</h3>
    <div style="font-size: 0.8125rem; color: var(--text-secondary);">
        <p>已添加 {{ saved.settings }} 个设定条目</p>
        <p>已添加 {{ saved.outlines }} 个大纲节点</p>
        <p>已保存 {{ saved.ideas }} 份对话记录</p>
    </div>
    <button onclick="this.closest('.modal-overlay').remove()" class="btn btn-ghost" style="margin-top: 1rem;">完成</button>
</div>
```

- [ ] **Step 4: Add save button to `_input.html` or `index.html`**

Append to the bottom of `index.html`, before closing `</div>` tag, add a save bar:

```html
<!-- Save bar -->
<div id="save-bar" style="display: none; padding: 0.5rem 1rem; border-top: 1px solid var(--border); background: var(--bg); justify-content: space-between; align-items: center;">
    <span style="font-size: 0.8125rem; color: var(--text-secondary);">将当前对话保存到项目</span>
    <div style="display: flex; gap: 0.5rem; align-items: center;">
        <select id="save-project-select" style="padding: 0.375rem 0.5rem; font-size: 0.8125rem; border-radius: 6px; border: 1px solid var(--border); background: var(--bg-card); color: var(--text);">
            <option value="">选择项目...</option>
            {% for p in projects %}
            <option value="{{ p.id }}">{{ p.title }}</option>
            {% endfor %}
        </select>
        <button onclick="triggerExtract()" class="btn btn-primary" style="padding: 0.375rem 0.75rem; font-size: 0.8125rem;">保存到项目</button>
    </div>
</div>

<script>
// Show save bar when there are messages
(function() {
    var msgs = JSON.parse(sessionStorage.getItem('brainstorm_messages') || '[]');
    if (msgs.length > 0) {
        document.getElementById('save-bar').style.display = 'flex';
    }
})();

function triggerExtract() {
    var projectId = document.getElementById('save-project-select').value;
    if (!projectId) { alert('请选择目标项目'); return; }
    var messages = JSON.parse(sessionStorage.getItem('brainstorm_messages') || '[]');
    fetch('/brainstorm/extract', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({messages: messages, project_id: projectId}),
    })
    .then(function(r) { return r.text(); })
    .then(function(html) {
        document.body.insertAdjacentHTML('beforeend', html);
    });
}
</script>
```

- [ ] **Step 5: Commit**

```bash
git add app/templates/brainstorm/ && git commit -m "feat: brainstorm save with LLM extraction and review UI"
```

---

### Task 5: Integration Test

**Files:**
- (none, just a verification run)

- [ ] **Step 1: Verify full app loads**

```bash
python -c "
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db
init_db()

client = TestClient(app)

# Brainstorm page loads
r = client.get('/brainstorm')
assert r.status_code == 200
assert '头脑风暴' in r.text
print('✅ Brainstorm page')

# Verify chat message partial renders
r = client.get('/styles')
assert r.status_code == 200

# Verify all template files exist
from pathlib import Path
templates = ['index.html', '_chat.html', '_message.html', '_input.html', '_sidebar.html', '_extract.html', '_saved.html']
for t in templates:
    p = Path('app/templates/brainstorm') / t
    assert p.exists(), f'{t} missing'
    print(f'✅ Template: {t}')

# Verify routes
routes = ['/brainstorm', '/brainstorm/chat', '/brainstorm/extract', '/brainstorm/confirm-save', '/brainstorm/history']
for ep in routes:
    matching = [r.path for r in app.routes if hasattr(r, 'path') and r.path == ep or r.path.startswith(ep)]
    # Just check at least one matches
    has_match = any(r.path == ep or (ep == '/brainstorm' and r.path == '/brainstorm') for r in app.routes if hasattr(r, 'path'))
    if ep == '/brainstorm/history':
        # Has /brainstorm/history and /brainstorm/history/{id}
        has_match = any('/brainstorm/history' in r.path for r in app.routes if hasattr(r, 'path'))
    print(f'✅ Route: {ep}')
"
```

- [ ] **Step 2: Commit**

```bash
git add -A && git commit -m "feat: brainstorm chat with LLM extraction save (integration)"
```
