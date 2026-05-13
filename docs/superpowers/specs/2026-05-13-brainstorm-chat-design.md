# Brainstorm Chat — Conversational AI Design

> 版本：v1.0
> 日期：2026-05-13
> 状态：设计完成，待实现

---

## 1. 概述

将头脑风暴模块从"表单提交→结果展示"改造为**对话式 AI 交互**，参考 ChatGPT/Claude/Kimi 等网页 AI 的交互模式。

### 核心变化

| 当前 | 改造后 |
|------|--------|
| 单次输入，单次输出 | 多轮对话，上下文累积 |
| 三种独立模式（自由/上下文/定向） | 同一对话入口，用户自然语言表达意图 |
| 结果以卡片形式展示 | 消息列表流式展示，支持 Markdown |
| 无历史记录 | sessionStorage 暂存 + "保存到项目"持久化 |
| 后端有状态区分模式 | 后端 stateless，前端传递完整消息历史 |

---

## 2. 交互流程

```
用户进入页面
  │
  ├─ sessionStorage 有历史 → 恢复对话
  ├─ sessionStorage 无历史 → 显示空对话（含系统提示）
  │
  ▼
用户输入消息 → Enter 发送
  │
  ├─ 前端将消息追加到 messages[]
  ├─ POST /brainstorm/chat {messages: [...]}
  │
  ▼
后端收到完整历史 → 调用 LLM → 返回回复
  │
  ├─ 前端追加回复到 messages[]
  ├─ 存入 sessionStorage
  ├─ 渲染消息列表
  │
  ▼
用户可选：
  ├─ 继续对话（回到输入）
  ├─ 保存到项目（POST /brainstorm/save）
  ├─ 新建对话（清空 sessionStorage）
  └─ 查看/加载历史记录
```

---

## 3. 接口设计

### POST /brainstorm/chat

核心聊天接口。前端发送完整消息历史，后端追加回复。

**Request:**
```json
{
  "messages": [
    {"role": "system", "content": "你是一位创意策划顾问..."},
    {"role": "user", "content": "我想写一个关于时间循环的故事"},
    {"role": "assistant", "content": "好的，这里有几个方向..."},
    {"role": "user", "content": "第三个方向再深入一下"}
  ],
  "project_id": "可选，用于上下文风暴"
}
```

**Response:**
```json
{
  "role": "assistant",
  "content": "关于时间循环中的道德困境..."
}
```

### POST /brainstorm/save

将当前对话保存到项目。

**Request:**
```json
{
  "project_id": "pid",
  "title": "创意构思 - 时间循环",
  "messages": [...]
}
```

**Response:** HTML 片段（更新历史列表侧栏）

### GET /brainstorm/history

已保存对话列表（HTMX 侧栏用）。

**Response:** HTML 片段

### GET /brainstorm/history/{id}

加载某条已保存记录的完整消息列表。

**Response:** HTML 片段（填充消息区域）

---

## 4. 后端改动

### BrainstormService → 新增 chat 方法

```python
@staticmethod
async def chat(db, messages: list[dict], project_id: str | None = None) -> str:
    adapter = get_adapter(db)
    # 如果是项目上下文模式，注入设定集信息
    if project_id:
        builder = ContextBuilder(db)
        context = builder.build_context_summary(project_id)
        # 将 context 注入到 system prompt
        ...
    response = await adapter.generate(messages, temperature=0.9, max_tokens=2048)
    record_usage(db, ...)
    return response.content
```

### 路由简化

原 `POST /brainstorm/generate` 废弃，替换为 `POST /brainstorm/chat`。原有三种模式的切换逻辑移除，统一由用户自然语言在对话中表达意图。

---

## 5. 前端设计

### 页面结构

```
app/templates/brainstorm/
├── index.html        ← 主页面：左侧历史 + 右侧聊天
├── _chat.html        ← 消息列表区域
├── _message.html     ← 单条消息（用户/AI）
├── _input.html       ← 输入框区域
└── _sidebar.html     ← 左侧历史列表
```

### 消息渲染

- 用户消息：右侧气泡，暖色背景
- AI 回复：左侧气泡，卡片背景，支持 Markdown
- Markdown 用 JavaScript 轻量渲染（支持 **粗体**、代码块、列表即可）
- 系统提示：顶部灰色小字，可折叠

### sessionStorage 管理

```javascript
const STORAGE_KEY = 'brainstorm_messages';

function loadMessages() {
    const data = sessionStorage.getItem(STORAGE_KEY);
    return data ? JSON.parse(data) : [];
}

function saveMessages(messages) {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
}

function newSession() {
    sessionStorage.removeItem(STORAGE_KEY);
    // 重新加载页面
}
```

### 输入交互

- 文本域支持 Enter 发送，Shift+Enter 换行
- 发送后清空输入框，禁用按钮直到收到回复
- 回复期间显示"思考中..."打字动画

### 左侧历史列表

- 用 HTMX 从 `/brainstorm/history` 加载
- 点击条目 → 加载对应对话到右侧
- "新建对话"按钮 → 清空 sessionStorage 刷新

---

## 6. 数据存储

### 临时存储：sessionStorage

- 当前对话消息（刷新页面保留）
- 关闭标签页自动清除

### 持久存储：复用 Ideas 表

保存对话时，将完整消息列表存入 `Idea` 表的 `content` 字段（JSON），`promoted_to_type = "chat"` 标记。无需新建表。

---

## 7. 与现有设计系统的整合

- 消息气泡使用 CSS 变量 `var(--bg-card)`、`var(--accent-light)` 等，自动适配深色模式
- 打字动画用 CSS keyframes
- 整体布局响应式：小屏幕隐藏历史侧栏，用汉堡菜单展开

---

## 8. 不实现的范围

- **流式输出（SSE）**：当前架构下实现 SSE 需要较大改动（FastAPI StreamingResponse + EventSource 前端），第一阶段不做。后续可迭代。
- **对话分支/编辑**：类 Claude 的对话编辑功能暂不实现。
- **多会话管理**：仅当前会话 + 已保存历史，不支持同时打开多个会话。
