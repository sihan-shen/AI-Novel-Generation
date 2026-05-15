# AI Outline Generation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add AI-powered outline generation to the existing outline manager — generate volumes/chapters/sections/content from story description and setting context.

**Architecture:** New OutlineGenerationService (separate from OutlineService) with 4 generation methods. Results previewed via streaming, confirmed via a batch-create endpoint. Prompt files in `app/llm/prompts/`.

**Tech Stack:** FastAPI, Jinja2/HTMX, SQLAlchemy, Claude/OpenAI API (streaming via SSE), existing OutlineService for DB writes.

---

### Task 1: Prompt Files

**Files:**
- Create: `app/llm/prompts/outline_gen_volume.txt`
- Create: `app/llm/prompts/outline_gen_chapter.txt`
- Create: `app/llm/prompts/outline_gen_section.txt`
- Create: `app/llm/prompts/outline_gen_content.txt`

- [ ] **Step 1: Create `app/llm/prompts/outline_gen_volume.txt`**

```
你是一名小说大纲策划师。根据作者的故事描述，设计整部小说的卷（卷=全书的大章节划分）结构。

## 输出规范

每个卷包含：标题(title)、概要(summary)
- 卷的数量 3-8 卷，取决于故事复杂度
- 每卷应有明确的故事阶段目标（开局、发展、转折、高潮、收束）
- 标题要精炼有吸引力，概要 1-2 句话说明本卷核心内容
- 严格基于作者提供的设定，不要自行添加故事元素

## 输出格式

只输出 JSON，不包含其他文字：
{"volumes": [{"title": "卷标题", "summary": "本卷核心内容描述"}]}
```

- [ ] **Step 2: Create `app/llm/prompts/outline_gen_chapter.txt`**

```
你是一名小说大纲策划师。根据指定卷的内容，设计该卷下的章节结构。

## 输入

你会收到：
- 项目设定上下文
- 当前卷的标题和概要
- 要求生成的章节数量（如果不指定则自动决定，通常 5-12 章）

## 输出规范

每个章节包含：标题(title)、概要(summary)
- 章与章之间应有情节推进和连贯性
- 每章应有明确的功能（引入、铺垫、冲突、转折、解决）
- 标题要体现本章核心事件

## 输出格式

只输出 JSON，不包含其他文字：
{"chapters": [{"title": "章标题", "summary": "本章核心内容"}]}
```

- [ ] **Step 3: Create `app/llm/prompts/outline_gen_section.txt`**

```
你是一名小说细纲策划师。根据指定章节的内容，设计该章节下的细纲节点（节）。

## 输入

你会收到：
- 项目设定上下文
- 当前章的标题和概要
- 需要展开的场景数量

## 输出规范

每个细纲节点包含：标题(title)、概要(summary)、写作说明(notes)
- 每个节点对应一个叙事单元（场景、段落、情节点）
- 说明写作用意：渲染氛围、推进剧情、揭示信息、角色塑造等
- 如果该章节涉及重要设定，标注需要参考的设定名称

## 输出格式

只输出 JSON，不包含其他文字：
{"sections": [{"title": "场景名称", "summary": "场景内容描述", "notes": "写作要点或参考设定"}]}
```

- [ ] **Step 4: Create `app/llm/prompts/outline_gen_content.txt`**

```
你是一名小说作者。根据细纲节点和项目设定，撰写完整的章节正文。

## 输入

你会收到：
- 项目设定上下文（人物、世界观等）
- 目标章节的细纲（多个场景）
- 前文摘要（如果是后续章节）

## 写作要求

- 使用流畅的中文叙事，保持文风一致
- 每节 1000-3000 字
- 融入设定集中的信息，保持设定一致
- 注意节奏：对话、描写、动作交替
- 直接输出正文，以 # 标题 开头

## 输出格式

直接输出正文，不需要 JSON 包裹。
```

- [ ] **Step 5: Commit**

```bash
git add app/llm/prompts/outline_gen_*.txt && git commit -m "feat: outline generation prompt files"
```

---

### Task 2: OutlineGenerationService

**Files:**
- Create: `app/services/outline_gen_service.py`

- [ ] **Step 1: Create `app/services/outline_gen_service.py`**

```python
import json
from typing import AsyncGenerator
from sqlalchemy.orm import Session
from app.llm.adapter import get_adapter
from app.llm.prompts.loader import load as load_prompt
from app.services.outline_service import OutlineService
from app.schemas.outline import OutlineCreate


class OutlineGenerationError(Exception):
    pass


class OutlineGenerationService:
    """AI-powered outline generation, step by step."""

    @staticmethod
    async def generate_volumes_stream(
        db: Session, project_id: str, story_desc: str, setting_ids: list[str] | None = None
    ) -> AsyncGenerator[str, None]:
        """Generate volume structure from story description."""
        prompt = load_prompt("outline_gen_volume")
        context = OutlineGenerationService._build_context(db, project_id, setting_ids)

        system_content = prompt
        if context:
            system_content += f"\n\n## 项目设定参考\n{context}"

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": f"请根据以下故事描述，设计整部小说的卷结构：\n\n{story_desc}"},
        ]

        adapter = get_adapter(db)
        async for chunk in adapter.generate_stream(messages, temperature=0.7, max_tokens=4096):
            yield chunk

    @staticmethod
    async def generate_chapters_stream(
        db: Session, project_id: str, volume_title: str, volume_summary: str, count: int = 0
    ) -> AsyncGenerator[str, None]:
        """Generate chapters under a volume."""
        prompt = load_prompt("outline_gen_chapter")
        context = OutlineGenerationService._build_context(db, project_id)

        system_content = prompt
        if context:
            system_content += f"\n\n## 项目设定参考\n{context}"

        user_msg = f"卷标题：{volume_title}\n卷概要：{volume_summary}\n"
        if count > 0:
            user_msg += f"请生成 {count} 章。"
        else:
            user_msg += "请根据卷的内容自动决定章节数量。"

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_msg},
        ]

        adapter = get_adapter(db)
        async for chunk in adapter.generate_stream(messages, temperature=0.7, max_tokens=4096):
            yield chunk

    @staticmethod
    async def generate_sections_stream(
        db: Session, project_id: str, chapter_title: str, chapter_summary: str, count: int = 0
    ) -> AsyncGenerator[str, None]:
        """Generate sections under a chapter."""
        prompt = load_prompt("outline_gen_section")
        context = OutlineGenerationService._build_context(db, project_id)

        system_content = prompt
        if context:
            system_content += f"\n\n## 项目设定参考\n{context}"

        user_msg = f"章标题：{chapter_title}\n章概要：{chapter_summary}\n"
        if count > 0:
            user_msg += f"请生成 {count} 个细节点。"
        else:
            user_msg += "请根据章的内容自动决定细节点数量。"

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_msg},
        ]

        adapter = get_adapter(db)
        async for chunk in adapter.generate_stream(messages, temperature=0.7, max_tokens=4096):
            yield chunk

    @staticmethod
    async def generate_content_stream(
        db: Session, project_id: str, chapter_title: str, sections: list[dict]
    ) -> AsyncGenerator[str, None]:
        """Generate chapter content from sections."""
        prompt = load_prompt("outline_gen_content")
        context = OutlineGenerationService._build_context(db, project_id)

        system_content = prompt
        if context:
            system_content += f"\n\n## 项目设定参考\n{context}"

        sections_text = "\n".join(
            f"- {s.get('title', '')}: {s.get('summary', '')}（{s.get('notes', '')}）"
            for s in sections
        )

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": f"章标题：{chapter_title}\n\n细纲：\n{sections_text}\n\n请根据以上细纲撰写正文。"},
        ]

        adapter = get_adapter(db)
        async for chunk in adapter.generate_stream(messages, temperature=0.8, max_tokens=8192):
            yield chunk

    @staticmethod
    def confirm_save(db: Session, project_id: str, items: list[dict], parent_id: str | None = None) -> int:
        """Batch save generated outlines to DB. Returns count saved."""
        count = 0
        for item in items:
            data = OutlineCreate(
                project_id=project_id,
                parent_id=parent_id,
                level=item.get("level", 1),
                title=item.get("title", ""),
                summary=item.get("summary", ""),
                notes=item.get("notes", ""),
            )
            # If it has children, save recursively
            children = item.pop("children", None)
            obj = OutlineService.create(db, data)
            count += 1
            if children:
                count += OutlineGenerationService.confirm_save(db, project_id, children, obj.id)
        return count

    @staticmethod
    def _build_context(db: Session, project_id: str, setting_ids: list[str] | None = None) -> str:
        """Build project context string for prompts."""
        from app.services.setting_service import SettingService
        return SettingService.build_llm_context(db, project_id, setting_ids)
```

- [ ] **Step 2: Verify imports**

```bash
source .venv/bin/activate
python -c "from app.services.outline_gen_service import OutlineGenerationService; print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add app/services/outline_gen_service.py && git commit -m "feat: outline generation service with streaming methods"
```

---

### Task 3: Router Endpoints

**Files:**
- Create: `app/routers/outline_gen.py`
- Modify: `app/main.py`

- [ ] **Step 1: Create `app/routers/outline_gen.py`**

```python
import json
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session
from pathlib import Path
from fastapi.templating import Jinja2Templates

from app.database import get_db
from app.services.outline_gen_service import OutlineGenerationService
from app.services.project_service import ProjectService
from app.services.setting_service import SettingService

router = APIRouter(prefix="/project/{project_id}/outline/generate", tags=["outline_gen"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("")
async def generate_page(project_id: str, request: Request, db: Session = Depends(get_db)):
    project = ProjectService.get(db, project_id)
    if not project:
        return HTMLResponse("Not found", 404)
    settings = SettingService.list_by_project(db, project_id)
    return templates.TemplateResponse(request, "outline/_generate.html", {
        "project": project, "settings": settings,
    })


@router.post("/volumes")
async def generate_volumes(project_id: str, request: Request, db: Session = Depends(get_db)):
    body = await request.json()
    story_desc = body.get("story_desc", "")
    setting_ids = body.get("setting_ids", [])

    async def event_stream():
        async for chunk in OutlineGenerationService.generate_volumes_stream(db, project_id, story_desc, setting_ids):
            yield f"data: {json.dumps({'content': chunk})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/chapters")
async def generate_chapters(project_id: str, request: Request, db: Session = Depends(get_db)):
    body = await request.json()
    async def event_stream():
        async for chunk in OutlineGenerationService.generate_chapters_stream(
            db, project_id, body.get("volume_title", ""), body.get("volume_summary", ""), int(body.get("count", 0))
        ):
            yield f"data: {json.dumps({'content': chunk})}\n\n"
        yield "data: [DONE]\n\n"
    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/sections")
async def generate_sections(project_id: str, request: Request, db: Session = Depends(get_db)):
    body = await request.json()
    async def event_stream():
        async for chunk in OutlineGenerationService.generate_sections_stream(
            db, project_id, body.get("chapter_title", ""), body.get("chapter_summary", ""), int(body.get("count", 0))
        ):
            yield f"data: {json.dumps({'content': chunk})}\n\n"
        yield "data: [DONE]\n\n"
    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/content")
async def generate_content(project_id: str, request: Request, db: Session = Depends(get_db)):
    body = await request.json()
    sections = body.get("sections", [])
    async def event_stream():
        async for chunk in OutlineGenerationService.generate_content_stream(
            db, project_id, body.get("chapter_title", ""), sections
        ):
            yield f"data: {json.dumps({'content': chunk})}\n\n"
        yield "data: [DONE]\n\n"
    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/confirm")
async def confirm_generation(project_id: str, request: Request, db: Session = Depends(get_db)):
    body = await request.json()
    items = body.get("items", [])
    parent_id = body.get("parent_id")
    count = OutlineGenerationService.confirm_save(db, project_id, items, parent_id)
    return templates.TemplateResponse(request, "outline/_confirm_result.html", {
        "count": count, "project_id": project_id,
    })
```

- [ ] **Step 2: Register router in `app/main.py`**

At imports:
```python
from app.routers import outline_gen
```
After other includes:
```python
app.include_router(outline_gen.router)
```

- [ ] **Step 3: Verify imports**

```bash
source .venv/bin/activate
python -c "from app.routers.outline_gen import router; print('Router OK')"
```

- [ ] **Step 4: Commit**

```bash
git add app/routers/outline_gen.py app/main.py && git commit -m "feat: outline generation router with streaming endpoints"
```

---

### Task 4: UI Templates

**Files:**
- Create: `app/templates/outline/_generate.html`
- Create: `app/templates/outline/_generate_result.html`
- Create: `app/templates/outline/_confirm_result.html`
- Modify: `app/templates/outline/index.html`

- [ ] **Step 1: Create `app/templates/outline/_generate.html`**

Modal form for AI generation:

```html
<div class="modal-overlay">
    <div class="modal-content" style="width: 100%; max-width: 560px; padding: 1.75rem; max-height: 85vh; overflow-y: auto;" onclick="event.stopPropagation()">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.5rem;">
            <h2 class="heading" style="margin: 0;">AI 生成大纲</h2>
            <button class="btn-icon" onclick="this.closest('.modal-overlay').remove()">✕</button>
        </div>

        <div style="margin-bottom: 1rem;">
            <label class="input-label">故事描述 *</label>
            <textarea id="gen-story-desc" rows="5" class="input" placeholder="输入你的故事梗概、核心设定、想表达的主题..."
                      style="resize: vertical;">{{ project.description }}</textarea>
        </div>

        <div style="margin-bottom: 1.25rem;">
            <label class="input-label">参考设定</label>
            <div style="display: flex; flex-direction: column; gap: 0.375rem; max-height: 160px; overflow-y: auto; padding: 0.5rem; border: 1px solid var(--border); border-radius: var(--radius-sm);">
                <label style="display: flex; align-items: center; gap: 0.375rem; font-size: 0.8125rem; cursor: pointer; padding: 0.25rem 0;">
                    <input type="checkbox" id="select-all-settings" checked onchange="document.querySelectorAll('.setting-checkbox').forEach(c=>c.checked=this.checked)">
                    <span style="font-weight: 500;">全选</span>
                </label>
                {% for s in settings %}
                <label style="display: flex; align-items: center; gap: 0.375rem; font-size: 0.8125rem; cursor: pointer; padding: 0.1875rem 0;">
                    <input type="checkbox" class="setting-checkbox" value="{{ s.id }}" checked>
                    <span>[{{ s.category }}] {{ s.name }}</span>
                </label>
                {% endfor %}
            </div>
        </div>

        <div style="margin-bottom: 1.25rem;">
            <label class="input-label">生成范围</label>
            <div style="display: flex; gap: 1rem; font-size: 0.8125rem;">
                <label style="display: flex; align-items: center; gap: 0.375rem; cursor: pointer;">
                    <input type="radio" name="gen-scope" value="volumes" checked> 仅卷结构
                </label>
                <label style="display: flex; align-items: center; gap: 0.375rem; cursor: pointer;">
                    <input type="radio" name="gen-scope" value="chapters"> 卷+章
                </label>
                <label style="display: flex; align-items: center; gap: 0.375rem; cursor: pointer;">
                    <input type="radio" name="gen-scope" value="full"> 完整(含细纲)
                </label>
            </div>
        </div>

        <div style="display: flex; justify-content: flex-end; gap: 0.5rem; border-top: 1px solid var(--border); padding-top: 1.125rem;">
            <button class="btn btn-ghost" onclick="this.closest('.modal-overlay').remove()">取消</button>
            <button class="btn btn-primary" onclick="startGeneration('{{ project.id }}')">开始生成</button>
        </div>
    </div>
</div>

<script>
function startGeneration(projectId) {
    var storyDesc = document.getElementById('gen-story-desc').value.trim();
    if (!storyDesc) { alert('请输入故事描述'); return; }
    var settingIds = [];
    document.querySelectorAll('.setting-checkbox:checked').forEach(function(cb) {
        settingIds.push(cb.value);
    });
    var scope = document.querySelector('input[name="gen-scope"]:checked').value;
    document.getElementById('generation-result').innerHTML = '<div style="text-align:center;padding:2rem;color:var(--text-secondary);">生成中...</div>';

    // Close modal
    document.querySelector('.modal-overlay').remove();

    var messages = [{role: 'user', content: storyDesc}];
    var fullResponse = '';

    fetch('/project/' + projectId + '/outline/generate/volumes', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({story_desc: storyDesc, setting_ids: settingIds}),
    })
    .then(function(r) {
        var reader = r.body.getReader();
        var decoder = new TextDecoder();
        var buffer = '';

        function read() {
            return reader.read().then(function(result) {
                if (result.done) {
                    renderGenerationResult(projectId, fullResponse, scope);
                    return;
                }
                buffer += decoder.decode(result.value, {stream: true});
                var lines = buffer.split('\n');
                buffer = lines.pop() || '';
                for (var i = 0; i < lines.length; i++) {
                    var line = lines[i].trim();
                    if (line.startsWith('data: ')) {
                        var data = line.slice(6);
                        if (data === '[DONE]') continue;
                        try {
                            var parsed = JSON.parse(data);
                            if (parsed.content) fullResponse += parsed.content;
                        } catch(e) {}
                    }
                }
                return read();
            });
        }
        return read();
    });
}

function renderGenerationResult(projectId, jsonStr, scope) {
    var container = document.getElementById('generation-result');
    try {
        var data = JSON.parse(jsonStr);
        var items = data.volumes || data.chapters || data.sections || [];
        var html = '<div class="card" style="padding:1rem;margin-top:1rem;"><h3 style="font-weight:600;margin-bottom:1rem;">📋 生成结果</h3>';
        html += '<div id="gen-editor">';
        items.forEach(function(item, i) {
            html += '<div style="margin-bottom:0.75rem;padding:0.75rem;border:1px solid var(--border);border-radius:var(--radius-sm);">';
            html += '<input class="input gen-title" value="' + escapeHtml(item.title || '') + '" style="font-weight:600;margin-bottom:0.375rem;" data-index="' + i + '">';
            html += '<textarea class="input gen-summary" rows="2" data-index="' + i + '" style="font-size:0.8125rem;">' + escapeHtml(item.summary || '') + '</textarea>';
            html += '</div>';
        });
        html += '</div>';
        html += '<div style="display:flex;justify-content:flex-end;gap:0.5rem;margin-top:0.75rem;padding-top:0.75rem;border-top:1px solid var(--border);">';
        html += '<button class="btn btn-ghost" onclick="document.getElementById(\'generation-result\').innerHTML=\'\'">舍弃</button>';
        html += '<button class="btn btn-primary" onclick="confirmGen(\'' + projectId + '\', \'' + scope + '\')">确认写入</button>';
        html += '</div></div>';
        container.innerHTML = html;
    } catch(e) {
        container.innerHTML = '<div class="card" style="padding:1rem;margin-top:1rem;"><p style="color:var(--text-secondary);">AI 返回格式异常，请重试。<br><pre style="font-size:0.75rem;margin-top:0.5rem;white-space:pre-wrap;">' + escapeHtml(jsonStr.slice(0, 500)) + '</pre></div>';
    }
}

function confirmGen(projectId, scope) {
    var items = [];
    var editors = document.querySelectorAll('#gen-editor > div');
    editors.forEach(function(div) {
        var titleInput = div.querySelector('.gen-title');
        var summaryInput = div.querySelector('.gen-summary');
        if (titleInput && titleInput.value.trim()) {
            items.push({level: scope === 'full' ? 3 : scope === 'chapters' ? 2 : 1, title: titleInput.value.trim(), summary: summaryInput ? summaryInput.value.trim() : ''});
        }
    });

    fetch('/project/' + projectId + '/outline/generate/confirm', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({items: items, parent_id: null}),
    })
    .then(function(r) { return r.text(); })
    .then(function(html) {
        document.getElementById('generation-result').innerHTML = html;
        htmx.trigger('#outline-tree', 'load');
    });
}

function escapeHtml(text) {
    var d = document.createElement('div');
    d.textContent = text;
    return d.innerHTML;
}
</script>
```

- [ ] **Step 2: Create `app/templates/outline/_generate_result.html`**

This is rendered inline by the JS in `_generate.html` — no separate file needed. The generation result is built via JS DOM manipulation inside the modal's callback.

- [ ] **Step 3: Create `app/templates/outline/_confirm_result.html`**

```html
<div style="padding: 1rem; text-align: center;">
    <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">✅</div>
    <p style="font-size: 0.9375rem; font-weight: 500;">已写入 {{ count }} 个条目</p>
    <p style="font-size: 0.8125rem; color: var(--text-secondary); margin-top: 0.25rem;">刷新大纲即可查看</p>
</div>
```

- [ ] **Step 4: Modify `app/templates/outline/index.html`**

Add an AI generate button and a result container:

Replace the existing `page-header-actions` div with:
```html
<div class="page-header-actions" style="display: flex; gap: 0.5rem;">
    <button hx-get="/project/{{ project.id }}/outline/generate"
            hx-target="body" hx-swap="beforeend"
            class="btn btn-primary" style="background: linear-gradient(135deg, var(--accent), #d4955a);">
        ✦ AI 生成大纲
    </button>
    <button hx-get="/project/{{ project.id }}/outline/new-item"
            hx-target="#outline-form-container" hx-swap="innerHTML"
            class="btn btn-ghost">
        + 手动添加
    </button>
</div>
```

Add a generation result container after `outline-form-container`:
```html
<div id="generation-result"></div>
```

- [ ] **Step 5: Verify templates render**

```bash
source .venv/bin/activate
python -c "
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db
init_db()
client = TestClient(app)

# Create a project
client.post('/projects/create', data={'title': 'Test', 'genre': '奇幻', 'description': 'A test story'})

# Get project id
r = client.get('/projects/list')
assert r.status_code == 200

# Verify generate modal template
from pathlib import Path
assert Path('app/templates/outline/_generate.html').exists()
assert Path('app/templates/outline/_confirm_result.html').exists()
print('All templates exist')

# Verify router mounted
routes = [r.path for r in app.routes if hasattr(r, 'path')]
gen_routes = [p for p in routes if 'outline/generate' in p]
print(f'Generation routes: {len(gen_routes)}')
assert len(gen_routes) >= 5
print('OK')
"
```

- [ ] **Step 6: Commit**

```bash
git add app/templates/outline/ && git commit -m "feat: outline generation UI with streaming, preview, and confirm"
```

---

### Task 5: Integration

- [ ] **Step 1: Full verification**

```bash
source .venv/bin/activate && python -c "
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db
init_db()
client = TestClient(app)

# Verify all generation routes
routes = [r.path for r in app.routes if hasattr(r, 'path') and 'outline/generate' in r.path]
expected = ['/project/{project_id}/outline/generate', '/project/{project_id}/outline/generate/volumes',
            '/project/{project_id}/outline/generate/chapters', '/project/{project_id}/outline/generate/sections',
            '/project/{project_id}/outline/generate/content', '/project/{project_id}/outline/generate/confirm']
for ep in expected:
    assert any(ep == r for r in routes), f'{ep} missing'
    print(f'  ✅ {ep}')

# Verify prompts
from app.llm.prompts.loader import load
for name in ['outline_gen_volume', 'outline_gen_chapter', 'outline_gen_section', 'outline_gen_content']:
    p = load(name)
    assert len(p) > 50, f'{name} too short'
    print(f'  ✅ {name} ({len(p)} chars)')

# Verify service imports
from app.services.outline_gen_service import OutlineGenerationService
assert hasattr(OutlineGenerationService, 'generate_volumes_stream')
assert hasattr(OutlineGenerationService, 'confirm_save')
print('  ✅ Service imports')

print()
print('All integration checks passed!')
"
```

- [ ] **Step 2: Commit

```bash
git add -A && git commit -m "feat: AI outline generation integration"
```
