# Brainstorm Agent Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the standalone `/brainstorm` page into the Agent Chat as `AgentTask(task_type="brainstorm")`, reusing existing infrastructure.

**Architecture:** Brainstorm is a conversation mode within the existing Agent Chat. It uses `run_agent()` for each user turn with a brainstorm-specific system prompt and tools. Routing is by `task.type`, not a separate state machine. No new database models — just a `metadata` column on `AgentTask`.

**Tech Stack:** Python/FastAPI, SQLAlchemy, Server-Sent Events, vanilla JavaScript

---

## Task 1: Add `metadata` and `updated_at` columns to AgentTask

**Files:**
- Modify: `app/models/agent_task.py`

- [ ] **Step 1: Add columns to AgentTask model**

```python
# app/models/agent_task.py — add after the `completed_at` column
    updated_at = Column(DateTime, default=datetime.utcnow)
    metadata_json = Column(Text, default="{}", name="metadata")
```

Full model diff:

```python
# After line 22 (`last_committed_step` stays), add:
    metadata_json = Column(Text, default="{}", name="metadata")
    # After line 24 (`completed_at` stays), add:
    updated_at = Column(DateTime, default=datetime.utcnow)
```

- [ ] **Step 2: Add a `metadata` property for JSON access**

```python
# In AgentTask class, add property:
    @property
    def metadata(self) -> dict:
        import json
        try:
            return json.loads(self.metadata_json or "{}")
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_metadata(self, data: dict):
        import json
        self.metadata_json = json.dumps(data, ensure_ascii=False)

    def update_metadata(self, **kwargs):
        md = self.metadata
        md.update(kwargs)
        self.set_metadata(md)
```

- [ ] **Step 3: Run DB migration**

Run: `pytest tests/test_agent_router.py::test_agent_page_renders -v`
Expected: PASS (SQLite creates new columns via `create_all`)

- [ ] **Step 4: Verify columns exist**

```python
# Quick verification via Python
python -c "
from app.database import init_db, SessionLocal
init_db()
db = SessionLocal()
from app.models.agent_task import AgentTask
# Check columns
print([c.name for c in AgentTask.__table__.columns])
db.close()
"
```

Expected output includes `metadata` and `updated_at`

- [ ] **Step 5: Commit**

```bash
git add app/models/agent_task.py
git commit -m "feat: add metadata and updated_at columns to AgentTask"
```

---

## Task 2: Create Brainstorm system prompt

**Files:**
- Create: `app/agents/prompts/brainstorm_system.txt`

- [ ] **Step 1: Write the system prompt**

```text
你是一位资深的小说创作顾问。你的任务是帮助作者拓展创意、完善构思，而不是替他们写作。

## 工作方法

- 接到作者的初始想法后，先用 1-2 句话确认你的理解，再展开建议
- 每次聚焦一个层面：如果作者在说人物，就围绕人物深入，不要同时跳到世界观
- 提供选项而非结论：给出 2-3 个不同方向，让作者选择
- 适时追问：如果作者的描述太笼统，主动询问具体细节来引导思考
- 肯定加延伸：先认可作者的想法，再在此基础上做扩展或深化

## 工具使用

你可以使用搜索工具查阅项目的设定、大纲、已有章节内容作为参考，但搜索只是辅助。
优先发散、联想、创造新想法。只在需要确认已有内容时才查询，不要频繁搜索。

`save_inspiration` 用于提议保存有潜力的灵感。用户会在脑暴结束后选择性确认。

## 模式切换

你只负责创意讨论。如果用户发出明确的写作请求（"帮我写第一章"、"修改这段"等）：
1. 简要总结当前脑暴成果（1-2句话）
2. 输出 handoff 动作让系统切换回写作模式
不要拒绝用户或要求用户手动切换。

## 输出规范

- 使用 Markdown 格式化：**加粗**突出重点，必要时用小标题分层
- 有结构的输出：思路类内容用列表，对比类内容用表格
- 长度控制：单次回复不超过 300 字
- 语言风格：平实的中文，不做作

## 应避免

- 不要替作者做决定 — 提供可能性而非唯一答案
- 不要一次性输出过多内容导致信息过载
- 不要评价"这个想法很好/很棒"之类的空话 — 说明为什么它有潜力
- 不要重复作者已经说过的内容来填充回复
- 不要强行套用理论框架除非作者主动提及
- 不要主动结束对话 — 等待用户明确表示结束（系统会提供结束按钮）
```

- [ ] **Step 2: Commit**

```bash
git add app/agents/prompts/brainstorm_system.txt
git commit -m "feat: add brainstorm agent system prompt"
```

---

## Task 3: Create Brainstorm tools

**Files:**
- Create: `app/agents/tools/brainstorm.py`

- [ ] **Step 1: Write `save_inspiration` tool**

```python
"""Brainstorm Agent tool handlers."""

import json
import uuid
from sqlalchemy.orm import Session


def save_inspiration(
    db: Session,
    task_id: str,
    insp_type: str,
    title: str,
    content: str,
    category: str = "",
) -> str:
    """Propose saving a brainstorm result. Accumulates in task.metadata pending_inspirations.

    Args:
        insp_type: "idea" | "setting" | "outline"
        title: Short descriptive title
        content: The inspiration content
        category: Optional category (e.g. "角色", "世界观")
    """
    from app.models.agent_task import AgentTask

    task = db.query(AgentTask).filter(AgentTask.id == task_id).first()
    if not task:
        return json.dumps({"status": "error", "message": "Task not found"}, ensure_ascii=False)

    pending = task.metadata.get("pending_inspirations", [])
    proposal = {
        "id": str(uuid.uuid4())[:8],
        "type": insp_type,
        "title": title,
        "content": content[:2000],
        "category": category,
        "created_at": None,  # Will be set at save time
    }
    pending.append(proposal)
    task.update_metadata(pending_inspirations=pending)
    db.commit()

    return json.dumps({
        "status": "proposed",
        "proposal_id": proposal["id"],
        "message": f"灵感「{title}」已暂存，脑暴结束后可确认保存",
        "pending_count": len(pending),
    }, ensure_ascii=False)


def list_pending_inspirations(db: Session, task_id: str) -> str:
    """List all pending inspirations for the current brainstorm session."""
    from app.models.agent_task import AgentTask

    task = db.query(AgentTask).filter(AgentTask.id == task_id).first()
    if not task:
        return json.dumps([], ensure_ascii=False)

    pending = task.metadata.get("pending_inspirations", [])
    return json.dumps(pending, ensure_ascii=False)
```

- [ ] **Step 2: Commit**

```bash
git add app/agents/tools/brainstorm.py
git commit -m "feat: add brainstom save_inspiration tool"
```

---

## Task 4: Create Brainstorm Agent config

**Files:**
- Create: `app/agents/agents/brainstorm.py`

- [ ] **Step 1: Write `build_brainstorm_config()`**

```python
"""Brainstorm Agent configuration."""

from pathlib import Path
from app.agents.base import AgentConfig, Tool
from app.agents.tools.writing import lookup_settings, get_outline_context
from app.agents.tools.shared import search_any
from app.agents.tools.brainstorm import save_inspiration


def _load_prompt() -> str:
    prompt_path = Path(__file__).parent.parent / "prompts" / "brainstorm_system.txt"
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    return "You are a creative writing consultant."


def build_brainstorm_config(
    db,
    project_id: str,
    task_id: str,
    max_steps: int = 50,
    token_budget: int = 100_000,
) -> AgentConfig:
    """Build a Brainstorm Agent configuration."""
    return AgentConfig(
        system_prompt=_load_prompt(),
        tools=[
            Tool(
                name="lookup_settings",
                description="Search project settings by keywords. Args: keywords (list[str])",
                parameters={"type": "object", "properties": {"keywords": {"type": "array", "items": {"type": "string"}}}},
                handler=lambda **kw: lookup_settings(db, keywords=kw["keywords"], project_id=project_id),
            ),
            Tool(
                name="get_outline_context",
                description="Get outline tree. Args: outline_id (str, optional)",
                parameters={"type": "object", "properties": {"outline_id": {"type": "string"}}},
                handler=lambda **kw: get_outline_context(db, project_id=project_id, outline_id=kw.get("outline_id")),
            ),
            Tool(
                name="search_any",
                description="Cross-entity search. Args: q (str), type (str, optional), limit (int, optional)",
                parameters={"type": "object", "properties": {"q": {"type": "string"}, "type": {"type": "string"}, "limit": {"type": "integer"}}},
                handler=lambda **kw: search_any(db, q=kw.get("q", ""), type=kw.get("type", "all"), limit=kw.get("limit", 20)),
            ),
            Tool(
                name="save_inspiration",
                description="Propose saving a brainstorm result. Args: insp_type (str: idea|setting|outline), title (str), content (str), category (str, optional)",
                parameters={"type": "object", "properties": {"insp_type": {"type": "string"}, "title": {"type": "string"}, "content": {"type": "string"}, "category": {"type": "string"}}},
                handler=lambda **kw: save_inspiration(db, task_id=task_id, insp_type=kw["insp_type"], title=kw["title"], content=kw["content"], category=kw.get("category", "")),
            ),
        ],
        model="claude-sonnet-4-6",
        temperature=0.9,
        max_steps=max_steps,
        token_budget=token_budget,
    )
```

- [ ] **Step 2: Commit**

```bash
git add app/agents/agents/brainstorm.py
git commit -m "feat: add brainstorm agent config builder"
```

---

## Task 5: Add handoff action support to `run_agent()`

**Files:**
- Modify: `app/agents/base.py:118-126`

- [ ] **Step 1: Add handoff action parsing**

In `run_agent()`, after the `action == "finish"` check (line ~118), add:

```python
            if "action" in parsed and parsed["action"] == "handoff":
                return AgentRunResult(
                    steps=steps,
                    output=parsed.get("summary", ""),
                    blackboard_changes={},
                    status="handoff",
                    retry_count=llm_error_count,
                )
```

- [ ] **Step 2: Update the JSON format instruction in `run_agent()`**

Change the format description (line ~66-70) to include handoff:

```python
    messages[0]["content"] += (
        "\n\nYou MUST respond with valid JSON exactly matching one of these formats:\n"
        f'{{"thought": "<reasoning>", "tool": "<tool_name>", "args": {{...}}}}\n'
        f'{{"action": "finish", "summary": "<final summary>"}}\n'
        f'{{"action": "handoff", "summary": "<handoff summary>"}}\n\n'
        f"Available tools:\n{tool_schema_desc}"
    )
```

- [ ] **Step 3: Run existing tests to verify no regression**

Run: `pytest tests/test_agent_base.py -v`
Expected: All 8 tests PASS

- [ ] **Step 4: Commit**

```bash
git add app/agents/base.py
git commit -m "feat: add handoff action support to run_agent()"
```

---

## Task 6: Add intent detection and brainstorm routing to agent.py

**Files:**
- Modify: `app/routers/agent.py`

This is the largest task. We need to add: intent detection, project lock, active task detection, timeout check, brainstorm turn handling, handoff flow.

- [ ] **Step 1: Add imports and module-level lock dict at top of agent.py**

After existing imports (line ~18), add:

```python
import asyncio
from datetime import datetime, timedelta

_project_locks: dict[str, asyncio.Lock] = {}

def _get_project_lock(project_id: str) -> asyncio.Lock:
    if project_id not in _project_locks:
        _project_locks[project_id] = asyncio.Lock()
    return _project_locks[project_id]
```

- [ ] **Step 2: Add `_get_active_task()` helper**

```python
def _get_active_task(db: Session, project_id: str):
    """Get the currently active (running or waiting_user) task for a project."""
    return db.query(AgentTask).filter(
        AgentTask.project_id == project_id,
        AgentTask.status.in_(["running", "waiting_user"]),
    ).order_by(AgentTask.updated_at.desc()).first()
```

- [ ] **Step 3: Add `_detect_intent()` helper**

```python
async def _detect_intent(adapter, message: str) -> str:
    """Classify user intent as 'brainstorm', 'writing', or 'other'."""
    prompt = f"""用户消息: "{message}"

判断意图：
- "brainstorm": 创意帮助、灵感拓展、方案探索、设定讨论。
  隐含表达："还能怎么玩"、"卡住了"、"没思路"、"有什么推荐"、"给我几个方案"、"不知道怎么"、"不够精彩"
- "writing": 明确的写作/修改/生成请求。边界：即使用户表达困惑（"不知道怎么写第一章"），只要提到具体章节/写作动作，归类为 writing
- "other": 以上都不是

返回 JSON: {{"intent": "brainstorm|writing|other"}}"""

    try:
        response = await adapter.generate(
            [{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=50,
        )
        import json
        result = json.loads(response.content)
        return result.get("intent", "other")
    except Exception:
        return "other"
```

- [ ] **Step 4: Add `_check_timeout()` helper**

```python
def _check_timeout(db: Session, task: AgentTask) -> bool:
    """Check if the active task has timed out (15 min since last message)."""
    from app.models.agent_message import AgentMessage
    last_msg = db.query(AgentMessage).filter(
        AgentMessage.task_id == task.id,
    ).order_by(AgentMessage.created_at.desc()).first()

    if last_msg and last_msg.created_at:
        elapsed = datetime.utcnow() - last_msg.created_at
        if elapsed > timedelta(minutes=15):
            task.status = "timeout"
            task.completed_at = datetime.utcnow()
            db.commit()
            return True
    return False
```

- [ ] **Step 5: Add `_handle_brainstorm_turn()` coroutine**

```python
async def _handle_brainstorm_turn(
    db: Session,
    task: AgentTask,
    message: str,
    project_id: str,
    adapter,
) -> list[dict]:
    """Execute one turn of brainstorm: load history, run agent, persist response."""
    from app.agents.base import run_agent, Tool
    from app.agents.agents.brainstorm import build_brainstorm_config
    from app.agents.blackboard import Blackboard
    from app.agents.autonomy import AutonomyConfig

    # Check for commands
    if message.strip() in ("/done", "/end"):
        task.status = "completed"
        task.completed_at = datetime.utcnow()
        db.commit()
        return [{"type": "brainstorm_end", "message": "脑暴已结束", "pending_inspirations": task.metadata.get("pending_inspirations", [])}]

    if message.strip() in ("/cancel",):
        task.status = "cancelled"
        task.completed_at = datetime.utcnow()
        db.commit()
        return [{"type": "brainstorm_end", "message": "脑暴已取消"}]

    # Load recent message history (last 20 turns)
    from app.models.agent_message import AgentMessage
    recent_msgs = db.query(AgentMessage).filter(
        AgentMessage.task_id == task.id,
    ).order_by(AgentMessage.sequence).all()

    history = []
    for m in recent_msgs[-20:]:  # Last 20 messages
        history.append({"role": m.role, "content": m.content})

    # Build context with minimal project info + history
    from app.services.project_service import ProjectService
    project = ProjectService.get(db, project_id)
    context_lines = [f"项目: {project.title if project else project_id}"]
    if project and project.genre:
        context_lines.append(f"类型: {project.genre}")

    # Build agent config and run
    config = build_brainstorm_config(db=db, project_id=project_id, task_id=task.id)
    blackboard = Blackboard(
        project_id=project_id,
        task={"type": "brainstorm", "task_id": task.id},
        autonomy_config=AutonomyConfig(),
    )

    # User message as the input
    user_context = "\n".join(context_lines) + "\n\n用户消息: " + message
    blackboard._settings_context = "\n".join(context_lines)  # Minimal context

    # Override get_context_for to include history
    original_get_context = blackboard.get_context_for
    def _brainstorm_context(agent_type: str) -> str:
        base = original_get_context(agent_type)
        if history:
            hist_text = "\n\n=== 当前脑暴对话 ===\n"
            for h in history[-20:]:
                role_label = "用户" if h["role"] == "user" else "顾问"
                hist_text += f"\n{role_label}: {h['content'][:500]}"
            base += hist_text
        return base
    blackboard.get_context_for = _brainstorm_context

    result = await run_agent(config, blackboard, adapter)

    # Handle handoff
    if result.status == "handoff":
        task.status = "completed"
        task.completed_at = datetime.utcnow()
        db.commit()
        return [{
            "type": "brainstorm_handoff",
            "summary": result.output,
            "user_message": message,
            "pending_inspirations": task.metadata.get("pending_inspirations", []),
        }]

    # Persist assistant response as AgentMessage
    import uuid
    seq = len(recent_msgs) + 1
    user_msg_obj = AgentMessage(
        id=str(uuid.uuid4()),
        task_id=task.id,
        role="user",
        content=message[:2000],
        message_type="user_message",
        sequence=seq,
    )
    db.add(user_msg_obj)

    seq += 1
    assistant_msg = AgentMessage(
        id=str(uuid.uuid4()),
        task_id=task.id,
        role="assistant",
        content=result.output[:2000],
        message_type="agent_output",
        sequence=seq,
    )
    db.add(assistant_msg)
    task.total_steps = seq
    task.total_tokens = (task.total_tokens or 0) + result.steps[0].token_usage.get("input_tokens", 0) + result.steps[0].token_usage.get("output_tokens", 0) if result.steps else 0
    task.updated_at = datetime.utcnow()
    db.commit()

    # Build SSE events
    events = [{"type": "brainstorm_response", "content": result.output, "sequence": seq}]

    # Include tool calls if any
    for step in result.steps:
        events.append({
            "type": "tool_call",
            "tool": step.tool_name,
            "args": step.tool_args,
            "sequence": seq,
        })

    # Check turn limit
    turn_count = task.metadata.get("turn_count", 0) + 1
    task.update_metadata(turn_count=turn_count)
    db.commit()
    if turn_count >= 100:
        task.status = "completed"
        task.completed_at = datetime.utcnow()
        db.commit()
        events.append({"type": "brainstorm_end", "message": "已达到最大轮数(100)，脑暴自动结束", "pending_inspirations": task.metadata.get("pending_inspirations", [])})

    return events
```

- [ ] **Step 6: Commit**

```bash
git add app/routers/agent.py
git commit -m "feat: add brainstorm intent detection and routing helpers"
```

---

## Task 7: Modify SSE endpoint to route brainstom vs writing

**Files:**
- Modify: `app/routers/agent.py` — the `chat_stream()` endpoint

- [ ] **Step 1: Refactor the `event_stream()` inner coroutine**

Replace the existing `event_stream()` in `chat_stream()` with the new version that handles brainstorm routing:

```python
    async def event_stream():
        adapter = get_adapter(db)
        lock = _get_project_lock(project_id)

        # ---- Check for existing active task ----
        async with lock:
            active_task = _get_active_task(db, project_id)

            if active_task and active_task.task_type == "brainstorm":
                # Check timeout
                if _check_timeout(db, active_task):
                    yield f"event: brainstorm_end\ndata: {json.dumps({'message': '脑暴已超时', 'timeout': True}, ensure_ascii=False)}\n\n"
                    return

                # Handle brainstorm turn
                events = await _handle_brainstorm_turn(
                    db, active_task, body.message, project_id, adapter
                )

                # Handle handoff from brainstorm
                handoff_event = next((e for e in events if e["type"] == "brainstorm_handoff"), None)
                if handoff_event:
                    # Emit brainstorm end
                    yield f"event: brainstorm_end\ndata: {json.dumps({'message': '切换到写作模式', 'handoff': True}, ensure_ascii=False)}\n\n"

                    # Create new writing task with handoff context
                    task_def = {
                        "type": "write_chapter",
                        "chapter_outline_id": body.chapter_outline_id,
                        "target_words": body.target_words,
                        "handoff_from_brainstorm": True,
                        "handoff_message": handoff_event["user_message"],
                        "handoff_inspirations": handoff_event["pending_inspirations"],
                    }
                    # ... fall through to normal orchestrator flow with this task_def
                    # For now, just emit a message suggesting user re-sends
                    yield f"event: orchestrator_thought\ndata: {json.dumps({'text': '脑暴已完成，请重新发送写作请求'}, ensure_ascii=False)}\n\n"
                    return

                # Emit brainstorm events
                seq = 0
                for event in events:
                    seq += 1
                    yield f"event: {event['type']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"

                    # Persist non-tool events as AgentMessages (already persisted in _handle_brainstorm_turn for responses)
                return

            # ---- No active task: detect intent ----
            if active_task is None:
                # Check for explicit /brainstorm command
                if body.message.strip().startswith("/brainstorm"):
                    intent = "brainstorm"
                else:
                    intent = await _detect_intent(adapter, body.message)

                if intent == "brainstorm":
                    task_obj = AgentTask(
                        id=str(uuid.uuid4()),
                        project_id=project_id,
                        task_type="brainstorm",
                        target_desc=body.message[:500],
                        autonomy_config=json.dumps(AutonomyConfig().to_dict()),
                        orchestrator_state="BRAINSTORMING",
                        status="running",
                    )
                    db.add(task_obj)
                    db.commit()

                    # Emit initial event
                    yield f"event: agent_start\ndata: {json.dumps({'agent': 'brainstorm', 'task_id': task_obj.id}, ensure_ascii=False)}\n\n"

                    # Handle first brainstorm turn
                    events = await _handle_brainstorm_turn(
                        db, task_obj, body.message, project_id, adapter
                    )
                    seq = 0
                    for event in events:
                        seq += 1
                        yield f"event: {event['type']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
                    return

            # ---- Normal orchestrator flow (original code) ----
            autonomy = AutonomyConfig()
            task_def = {"type": "write_chapter", "chapter_outline_id": body.chapter_outline_id, "target_words": body.target_words}
            task_obj = AgentTask(
                id=str(uuid.uuid4()),
                project_id=project_id,
                task_type="write_chapter",
                target_desc=body.message[:500],
                autonomy_config=json.dumps(autonomy.to_dict()),
                orchestrator_state="RUNNING",
                status="running",
            )
            db.add(task_obj)
            db.commit()
            task_id = task_obj.id

            blackboard = Blackboard(project_id=project_id, task=task_def, autonomy_config=autonomy)
            orch = Orchestrator(db=db, blackboard=blackboard, adapter=adapter, task_id=task_id)
            orch_task = asyncio.create_task(orch.run())
            seq = 0

            try:
                while not orch_task.done() or not blackboard.events.empty():
                    try:
                        event = await asyncio.wait_for(blackboard.events.get(), timeout=0.5)
                        seq += 1
                        event["sequence"] = seq
                        yield f"event: {event['type']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"

                        content = event.get("text", event.get("summary", event.get("tool", "")))
                        msg = AgentMessage(
                            id=str(uuid.uuid4()),
                            task_id=task_id,
                            role="user" if event["type"] in ("user_message", "confirm_response") else "assistant",
                            content=str(content)[:2000],
                            message_type=event["type"],
                            msg_metadata=json.dumps(event, ensure_ascii=False),
                            sequence=seq,
                        )
                        db.add(msg)
                        db.commit()

                        if seq % 10 == 1:
                            task_obj.total_steps = seq
                            db.commit()
                    except asyncio.TimeoutError:
                        if orch_task.done():
                            break
            finally:
                final_state = blackboard.orchestrator_state
                task_obj.orchestrator_state = final_state
                task_obj.total_steps = seq
                task_obj.total_tokens = blackboard.cumulative_tokens
                if final_state in ("DONE", "CANCELLED", "IDLE"):
                    task_obj.status = "completed" if final_state == "DONE" else "cancelled"
                    task_obj.completed_at = datetime.utcnow()
                elif final_state == "WAITING_USER":
                    task_obj.status = "waiting_user"
                try:
                    task_obj.blackboard_snapshot = json.dumps(blackboard.to_snapshot(), ensure_ascii=False)
                except Exception:
                    pass
                db.commit()

            yield "event: done\ndata: {}\n\n"
```

- [ ] **Step 2: Run existing tests to verify no regression**

Run: `pytest tests/test_agent_router.py -v`
Expected: All 7 tests PASS

- [ ] **Step 3: Commit**

```bash
git add app/routers/agent.py
git commit -m "feat: add brainstorm routing to agent SSE endpoint"
```

---

## Task 8: Add `/brainstorm` 302 redirect

**Files:**
- Modify: `app/main.py` (or `app/routers/`)

- [ ] **Step 1: Add redirect route in main.py**

After the existing router includes (line ~26), add:

```python
from fastapi.responses import RedirectResponse

@app.get("/brainstorm")
async def brainstorm_redirect():
    """Redirect old /brainstorm page to agent chat."""
    return RedirectResponse(url="/", status_code=302)
```

Note: Since `/brainstorm` requires a project, redirect to dashboard where user can pick a project. If a `project_id` query param is provided, redirect to that project's agent page:

```python
@app.get("/brainstorm")
async def brainstorm_redirect(project_id: str | None = None):
    """Redirect old /brainstorm page to agent chat."""
    if project_id:
        return RedirectResponse(url=f"/project/{project_id}/agent", status_code=302)
    return RedirectResponse(url="/", status_code=302)
```

- [ ] **Step 2: Remove brainstorm router from main.py imports**

Comment out (don't delete yet) the brainstorm router registration:

```python
# Line 10: comment out brainstorming import
from app.routers import projects, outlines, settings, chapters, styles, reviews, ideas, config, outline_gen, search, agent
# from app.routers import brainstorming  # DEPRECATED: replaced by agent chat brainstorm mode

# Line 19: comment out router include
# app.include_router(brainstorming.router)  # DEPRECATED
```

- [ ] **Step 3: Verify app starts cleanly**

Run: `python -c "from app.main import app; print('OK')"`
Expected: OK (no import errors)

- [ ] **Step 4: Run full test suite**

Run: `pytest tests/ -v --ignore=tests/test_search_service.py --ignore=tests/test_search_router.py`
Expected: All tests PASS (no regression from removing brainstorm router)

- [ ] **Step 5: Commit**

```bash
git add app/main.py
git commit -m "feat: add /brainstorm 302 redirect, deprecate old brainstorm router"
```

---

## Task 9: Frontend changes — end/cancel buttons, mode indicator

**Files:**
- Modify: `app/static/js/agent-chat.js`

- [ ] **Step 1: Add brainstorm mode indicator and buttons to `_handleLiveEvent`**

In `_handleLiveEvent()`, after the existing event type handlers (line ~145), add:

```javascript
            // Brainstorm mode indicators
            if (type === 'agent_start' && data.agent === 'brainstorm') {
                this._showBrainstormControls(true);
                this._setStatus('脑暴中...');
            }
            if (type === 'brainstorm_response' && data.content) {
                var el = document.createElement('div');
                el.className = 'agent-message brainstorm-response';
                // Render markdown-like content
                el.innerHTML = this._renderBrainstormContent(data.content);
                messages.appendChild(el);
                messages.scrollTop = messages.scrollHeight;
            }
            if (type === 'brainstorm_end') {
                this._showBrainstormControls(false);
                this._setStatus('就绪');
                if (data.pending_inspirations && data.pending_inspirations.length > 0) {
                    this._showInspirationPanel(data.pending_inspirations);
                }
                if (data.message && typeof showToast === 'function') {
                    showToast(data.message, data.timeout ? 'warning' : 'info');
                }
            }
```

- [ ] **Step 2: Add brainstorm control methods**

Add to the `AgentChat` object:

```javascript
    _showBrainstormControls: function(show) {
        var container = document.getElementById('brainstorm-controls');
        if (!container) {
            // Create controls container
            container = document.createElement('div');
            container.id = 'brainstorm-controls';
            container.className = 'brainstorm-controls';
            container.style.cssText = 'display:flex;gap:0.5rem;align-items:center;padding:0.5rem 1rem;background:var(--bg-secondary);border-bottom:1px solid var(--border);';
            
            var indicator = document.createElement('span');
            indicator.className = 'brainstorm-indicator';
            indicator.style.cssText = 'font-size:0.8125rem;color:var(--text-secondary);flex:1;';
            
            var doneBtn = document.createElement('button');
            doneBtn.className = 'btn btn-sm btn-primary';
            doneBtn.textContent = '结束脑暴';
            var self = this;
            doneBtn.onclick = function() {
                self._sendCommand('/done');
            };
            
            var cancelBtn = document.createElement('button');
            cancelBtn.className = 'btn btn-sm btn-ghost';
            cancelBtn.textContent = '取消';
            cancelBtn.onclick = function() {
                self._sendCommand('/cancel');
            };
            
            container.appendChild(indicator);
            container.appendChild(doneBtn);
            container.appendChild(cancelBtn);
            
            var messages = this._msgContainer();
            messages.parentNode.insertBefore(container, messages);
        }
        container.style.display = show ? 'flex' : 'none';
        
        var indicator = container.querySelector('.brainstorm-indicator');
        if (indicator) indicator.textContent = '脑暴模式';
    },

    _sendCommand: function(cmd) {
        var input = document.getElementById('agent-input');
        if (input) {
            input.value = cmd;
            this.send(new Event('submit'));
        }
    },

    _renderBrainstormContent: function(text) {
        // Simple markdown rendering for brainstorm responses
        var html = text
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>');
        return '<p>' + html + '</p>';
    },

    _showInspirationPanel: function(inspirations) {
        var messages = this._msgContainer();
        var panel = document.createElement('div');
        panel.className = 'inspiration-panel card';
        panel.style.cssText = 'margin:1rem;padding:1rem;';
        
        var title = document.createElement('h4');
        title.className = 'heading-sm';
        title.textContent = '待保存的灵感 (' + inspirations.length + ')';
        panel.appendChild(title);
        
        for (var i = 0; i < inspirations.length; i++) {
            var insp = inspirations[i];
            var row = document.createElement('div');
            row.style.cssText = 'display:flex;align-items:flex-start;gap:0.5rem;padding:0.5rem 0;border-bottom:1px solid var(--border);';
            
            var cb = document.createElement('input');
            cb.type = 'checkbox';
            cb.checked = true;
            cb.dataset.inspId = insp.id;
            cb.style.cssText = 'margin-top:0.25rem;';
            
            var info = document.createElement('div');
            info.style.cssText = 'flex:1;';
            info.innerHTML = '<strong>' + insp.title + '</strong> <span style="color:var(--text-tertiary);font-size:0.75rem;">[' + insp.type + ']</span>' +
                '<div style="font-size:0.8125rem;color:var(--text-secondary);margin-top:0.25rem;">' + (insp.content || '').substring(0, 200) + '</div>';
            
            row.appendChild(cb);
            row.appendChild(info);
            panel.appendChild(row);
        }
        
        var actions = document.createElement('div');
        actions.style.cssText = 'display:flex;gap:0.5rem;justify-content:flex-end;margin-top:0.75rem;';
        
        var saveBtn = document.createElement('button');
        saveBtn.className = 'btn btn-sm btn-primary';
        saveBtn.textContent = '保存选中';
        var self = this;
        saveBtn.onclick = function() {
            var checkboxes = panel.querySelectorAll('input[type=checkbox]');
            var selected = [];
            for (var j = 0; j < checkboxes.length; j++) {
                if (checkboxes[j].checked) selected.push(checkboxes[j].dataset.inspId);
            }
            self._confirmInspirations(selected);
            panel.remove();
        };
        
        var dismissBtn = document.createElement('button');
        dismissBtn.className = 'btn btn-sm btn-ghost';
        dismissBtn.textContent = '全部丢弃';
        dismissBtn.onclick = function() { panel.remove(); };
        
        actions.appendChild(dismissBtn);
        actions.appendChild(saveBtn);
        panel.appendChild(actions);
        
        messages.appendChild(panel);
        messages.scrollTop = messages.scrollHeight;
    },

    _confirmInspirations: function(inspIds) {
        var projectId = window.location.pathname.split('/')[2];
        fetch('/project/' + projectId + '/agent/inspirations/confirm', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({inspiration_ids: inspIds}),
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.status === 'ok' && typeof showToast === 'function') {
                showToast('已保存 ' + data.saved_count + ' 条灵感', 'success');
            }
        })
        .catch(function() {
            if (typeof showToast === 'function') showToast('保存失败', 'error');
        });
    },
```

Also update `startNewSession()` to hide brainstorm controls:

```javascript
    startNewSession: function() {
        // ... existing code ...
        this._showBrainstormControls(false);  // Add this line
    },
```

- [ ] **Step 2: Commit**

```bash
git add app/static/js/agent-chat.js
git commit -m "feat: add brainstorm controls and inspiration panel to agent chat UI"
```

---

## Task 10: Add inspiration confirmation endpoint

**Files:**
- Modify: `app/routers/agent.py`

- [ ] **Step 1: Add POST `/inspirations/confirm` endpoint**

```python
class ConfirmInspirationsRequest(BaseModel):
    inspiration_ids: list[str]


@router.post("/inspirations/confirm")
async def confirm_inspirations(
    project_id: str,
    body: ConfirmInspirationsRequest,
    db: Session = Depends(get_db),
):
    """Confirm and save selected inspirations from a completed brainstorm session."""
    from app.services.idea_service import IdeaService
    from app.services.setting_service import SettingService
    from app.services.outline_service import OutlineService
    from app.schemas.setting import SettingCreate
    from app.schemas.outline import OutlineCreate

    # Find the most recent completed brainstorm task
    task = db.query(AgentTask).filter(
        AgentTask.project_id == project_id,
        AgentTask.task_type == "brainstorm",
        AgentTask.status == "completed",
    ).order_by(AgentTask.updated_at.desc()).first()

    if not task:
        return {"status": "error", "message": "No completed brainstorm session found"}

    pending = task.metadata.get("pending_inspirations", [])
    saved_count = 0

    for insp in pending:
        if insp["id"] not in body.inspiration_ids:
            continue
        if insp["type"] == "idea":
            IdeaService.create(
                db, project_id=project_id,
                title=insp.get("title", "灵感"),
                content=insp.get("content", ""),
                source="brainstorm",
            )
            saved_count += 1
        elif insp["type"] == "setting":
            SettingService.create(db, SettingCreate(
                project_id=project_id,
                category=insp.get("category", "自定义"),
                name=insp.get("title", "未命名"),
                summary=insp.get("content", "")[:500],
                content=insp.get("content", ""),
                weight=5,
            ))
            saved_count += 1
        elif insp["type"] == "outline":
            OutlineService.create(db, OutlineCreate(
                project_id=project_id,
                level=2,
                title=insp.get("title", "未命名"),
                summary=insp.get("content", "")[:500],
            ))
            saved_count += 1

    # Remove confirmed items from pending
    remaining = [i for i in pending if i["id"] not in body.inspiration_ids]
    task.update_metadata(pending_inspirations=remaining)
    db.commit()

    return {"status": "ok", "saved_count": saved_count}
```

- [ ] **Step 2: Commit**

```bash
git add app/routers/agent.py
git commit -m "feat: add inspiration confirmation endpoint"
```

---

## Task 11: Write tests

**Files:**
- Create: `tests/test_brainstorm_agent.py`

- [ ] **Step 1: Write test for BrainstormConfig construction**

```python
"""Tests for Brainstorm Agent."""
import json
import pytest
from app.agents.agents.brainstorm import build_brainstorm_config


def test_build_brainstorm_config(db_session):
    """Brainstorm config has the expected tools and settings."""
    config = build_brainstorm_config(
        db=db_session, project_id="p1", task_id="t1",
    )
    assert config.model == "claude-sonnet-4-6"
    assert config.temperature == 0.9
    assert config.max_steps == 50
    assert config.token_budget == 100_000

    tool_names = {t.name for t in config.tools}
    assert "lookup_settings" in tool_names
    assert "get_outline_context" in tool_names
    assert "search_any" in tool_names
    assert "save_inspiration" in tool_names
```

- [ ] **Step 2: Write test for save_inspiration tool**

```python
from app.models.project import Project
from app.models.agent_task import AgentTask
from app.agents.tools.brainstorm import save_inspiration


def test_save_inspiration_adds_to_pending(db_session):
    """save_inspiration accumulates proposals in task.metadata."""
    db_session.add(Project(id="p1", title="Test"))
    task = AgentTask(
        id="t1", project_id="p1", task_type="brainstorm",
        status="running",
    )
    db_session.add(task)
    db_session.commit()

    result = save_inspiration(
        db=db_session, task_id="t1",
        insp_type="idea", title="主角设定", content="一个退役的佣兵",
    )
    data = json.loads(result)
    assert data["status"] == "proposed"
    assert data["pending_count"] == 1

    # Verify persisted
    db_session.refresh(task)
    pending = task.metadata.get("pending_inspirations", [])
    assert len(pending) == 1
    assert pending[0]["title"] == "主角设定"
    assert pending[0]["type"] == "idea"


def test_save_inspiration_multiple_accumulates(db_session):
    """Multiple save_inspiration calls all accumulate."""
    db_session.add(Project(id="p1", title="Test"))
    task = AgentTask(
        id="t1", project_id="p1", task_type="brainstorm",
        status="running",
    )
    db_session.add(task)
    db_session.commit()

    save_inspiration(db=db_session, task_id="t1", insp_type="idea", title="A", content="a")
    save_inspiration(db=db_session, task_id="t1", insp_type="setting", title="B", content="b")

    db_session.refresh(task)
    pending = task.metadata.get("pending_inspirations", [])
    assert len(pending) == 2
```

- [ ] **Step 3: Write test for handoff action in run_agent**

```python
from app.agents.base import AgentConfig, Tool, run_agent
from app.agents.blackboard import Blackboard
from app.agents.autonomy import AutonomyConfig


@pytest.mark.asyncio
async def test_run_agent_handoff_action():
    """run_agent returns status='handoff' when agent emits handoff action."""
    bb = Blackboard(
        project_id="p1",
        task={"type": "brainstorm"},
        autonomy_config=AutonomyConfig(),
    )

    class FakeAdapter:
        async def generate(self, messages, **kwargs):
            from app.llm.adapter import LLMResponse
            return LLMResponse(
                content=json.dumps({"action": "handoff", "summary": "切换到写作"}),
                usage={"input_tokens": 10, "output_tokens": 5},
            )

        def count_tokens(self, text):
            return 10

    config = AgentConfig(
        system_prompt="You brainstorm.",
        tools=[],
        model="claude-sonnet-4-6",
    )

    result = await run_agent(config, bb, FakeAdapter())
    assert result.status == "handoff"
    assert result.output == "切换到写作"
```

- [ ] **Step 4: Write test for intent detection**

```python
from app.routers.agent import _detect_intent


class FakeIntentAdapter:
    async def generate(self, messages, **kwargs):
        from app.llm.adapter import LLMResponse
        msg = messages[-1]["content"]
        if "brainstorm" in msg.lower() or "灵感" in msg or "创意" in msg:
            return LLMResponse(
                content=json.dumps({"intent": "brainstorm"}),
                usage={"input_tokens": 10, "output_tokens": 3},
            )
        elif "写" in msg or "章节" in msg:
            return LLMResponse(
                content=json.dumps({"intent": "writing"}),
                usage={"input_tokens": 10, "output_tokens": 3},
            )
        return LLMResponse(
            content=json.dumps({"intent": "other"}),
            usage={"input_tokens": 10, "output_tokens": 3},
        )


@pytest.mark.asyncio
async def test_detect_intent_brainstorm():
    adapter = FakeIntentAdapter()
    result = await _detect_intent(adapter, "帮我脑暴一下主角设定")
    assert result == "brainstorm"


@pytest.mark.asyncio
async def test_detect_intent_writing():
    adapter = FakeIntentAdapter()
    result = await _detect_intent(adapter, "帮我写第一章")
    assert result == "writing"


@pytest.mark.asyncio
async def test_detect_intent_other():
    adapter = FakeIntentAdapter()
    result = await _detect_intent(adapter, "你好")
    assert result == "other"


@pytest.mark.asyncio
async def test_detect_intent_boundary():
    """即使困惑，提到具体章节 → writing."""
    adapter = FakeIntentAdapter()
    result = await _detect_intent(adapter, "不知道怎么写第一章")
    assert result == "writing"


@pytest.mark.asyncio
async def test_detect_intent_implicit():
    """隐含创意需求表达 → brainstorm."""
    adapter = FakeIntentAdapter()
    result = await _detect_intent(adapter, "这个剧情不够精彩")
    assert result == "brainstorm"
```

- [ ] **Step 5: Write test for /brainstorm 302 redirect**

```python
def test_brainstorm_redirect_to_dashboard(client):
    """Old /brainstorm URL redirects to dashboard."""
    response = client.get("/brainstorm", follow_redirects=False)
    assert response.status_code == 302


def test_brainstorm_redirect_with_project(client):
    """Old /brainstorm URL with project_id redirects to agent page."""
    from app.models.project import Project
    # Can't easily test follow_redirects with TestClient + project dependency
    response = client.get("/brainstorm?project_id=p1", follow_redirects=False)
    assert response.status_code == 302
    assert "p1" in response.headers.get("location", "")
```

- [ ] **Step 6: Run all tests**

Run: `pytest tests/test_brainstorm_agent.py tests/test_agent_base.py tests/test_agent_router.py -v`
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add tests/test_brainstorm_agent.py
git commit -m "test: add brainstorm agent tests"
```

---

## Task 12: Add brainstorm CSS

**Files:**
- Modify: `app/static/css/agent.css` (or create if needed)

- [ ] **Step 1: Add brainstorm-specific styles**

```css
/* Brainstorm Controls */
.brainstorm-controls {
    display: flex;
    gap: 0.5rem;
    align-items: center;
    padding: 0.5rem 1rem;
    background: var(--bg-secondary, #f8f5f0);
    border-bottom: 1px solid var(--border, #e0d8cc);
}

.brainstorm-indicator {
    font-size: 0.8125rem;
    color: var(--text-secondary, #6b5e4f);
    flex: 1;
}

/* Brainstorm Response */
.brainstorm-response {
    padding: 1rem;
    line-height: 1.7;
    font-size: 0.9375rem;
    color: var(--text-primary, #2c2416);
}

.brainstorm-response p {
    margin: 0.5rem 0;
}

.brainstorm-response strong {
    color: var(--accent, #8b5e3c);
}

/* Inspiration Panel */
.inspiration-panel {
    margin: 1rem;
    padding: 1rem;
    background: var(--bg-primary, #fff);
    border: 1px solid var(--border, #e0d8cc);
    border-radius: 8px;
}

.inspiration-panel h4 {
    margin: 0 0 0.75rem 0;
    font-size: 0.9375rem;
}
```

- [ ] **Step 2: Commit**

```bash
git add app/static/css/agent.css
git commit -m "style: add brainstorm mode CSS"
```

---

## Task 13: Final integration — run app and verify

- [ ] **Step 1: Start the dev server**

```bash
python -m app.main
```

- [ ] **Step 2: Manual verification checklist**

- [ ] Navigate to `/project/{id}/agent` — page renders
- [ ] Send a message like "帮我脑暴一下主角设定" — verify brainstorm mode activates
- [ ] Verify brainstorm controls (end/cancel buttons) appear
- [ ] Send a few brainstorm turns — verify history persists
- [ ] Click "结束脑暴" — verify brainstorm ends
- [ ] Verify `/brainstorm` redirects to dashboard
- [ ] Send a writing request — verify normal orchestrator flow still works
- [ ] Verify session list shows brainstorm tasks

- [ ] **Step 3: Run full test suite one final time**

```bash
pytest tests/ -v --ignore=tests/test_search_service.py --ignore=tests/test_search_router.py
```
Expected: All tests PASS

- [ ] **Step 4: Commit any final fixes**

```bash
git add -A
git commit -m "chore: integration fixes for brainstorm agent migration"
```
