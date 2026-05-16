# UX 增强设计文档

> **Status:** Approved · 2026-05-17
> **Scope:** 在现有 Literary Studio 设计基础上引入 16 项新交互能力，分四个方向：写作专注 / 快速导航 / AI 透明度 / 数据检索。
> **Architecture:** 统一命令中心（Cmd+K 一站式入口）+ 全局常驻状态栏 + 写作页深化 + 列表页轻量增强。
> **Implementation:** 单一设计、分期实施。本规范定义最终形态；实施计划负责拆分阶段。

---

## 1 · 目标与范围

### 1.1 目标

让 Novel Forge 从「功能完整」走向「用起来顺手」。具体地：

- 写作时不需切换页面就能看到所有关键状态（保存、字数、Token）
- 任何操作都可以通过 Cmd+K 一键到达
- AI 操作过程透明：成本可预估、进度可见、历史可回溯
- 数据量增长后仍能快速检索与批量处理

### 1.2 不在范围内

- 不重做现有 Literary Studio 视觉设计系统
- 不引入大型前端框架（React/Vue）
- 不改变现有路由结构（仅新增）
- 不处理多用户协作、版本控制、云同步等更大议题

### 1.3 成功标准

- 命令面板可在 200ms 内从任意页面唤起并完成首次输入响应
- 写作页底部状态栏在编辑期间不阻塞输入、不引发布局抖动
- AI 调用前的上下文预览能准确展示将要发送给模型的所有内容
- 全局搜索可在 1 万条混合实体上 300ms 内返回结果

---

## 2 · 架构总览

UI 被组织为四个**面**（surface）：

```
┌─────────────────────────────────────────────────────┐
│  Top Nav  (现有, 不动)                              │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Page Body  (各页面原有内容 + 局部增强)             │
│                                                     │
│  • 写作页：编辑器右上加专注/打字机切换按钮          │
│  • 列表页：每项 hover 出现 checkbox + ✎ 重命名      │
│  • 项目详情页：增加导出按钮                         │
│  • AI 调用按钮：先弹上下文预览模态                  │
│                                                     │
├─────────────────────────────────────────────────────┤
│  Global Status Bar  (新增, 全局常驻)                │
│  ●已保存 14:32  ·  字数(仅写作页)  ·  📊 24.5K     │
└─────────────────────────────────────────────────────┘

         ┌──────── ⌘K 唤起 ────────┐
         │ [全部|命令|项目|章节|...] │   命令面板
         │ 🔍 ___________            │   (Modal)
         │ ▸ 最近 5 项               │
         │ ▸ 常用命令                │
         └───────────────────────────┘

         ┌──────── 点击 📊 ────────┐
         │ Token 用量明细模态       │
         │ [今日|本周|本月]         │
         │ 模型 · 场景 · 项目分组    │
         └───────────────────────────┘
```

### 2.1 文件与代码组织

```
app/
├── static/                          (新增, FastAPI mount /static)
│   ├── js/
│   │   ├── palette.js               命令面板 (Alpine.js)
│   │   ├── status-bar.js            状态栏状态
│   │   ├── shortcuts.js             全局快捷键注册
│   │   ├── token-dashboard.js       Token 用量模态
│   │   ├── ai-context-preview.js    AI 调用前预览
│   │   ├── inline-rename.js         内联重命名通用组件
│   │   ├── bulk-select.js           批量选择通用组件
│   │   └── lib/                     第三方库本地副本
│   │       ├── alpine.min.js        (~7KB)
│   │       └── fuse.min.js          (~12KB)
│   └── css/
│       └── enhancements.css         新组件样式（避免污染 base.html）
├── templates/
│   ├── _palette.html                命令面板模板
│   ├── _status_bar.html             全局状态栏
│   ├── _token_dashboard.html        Token 模态
│   ├── _ai_context_preview.html     AI 上下文预览模态
│   ├── ai_history/                  新增页面
│   │   ├── index.html
│   │   └── _list.html
│   └── ...
├── routers/
│   ├── search.py                    (新增) 全局搜索 API
│   ├── token_usage.py               (新增) Token 用量 API
│   ├── ai_history.py                (新增) AI 历史 API
│   └── export.py                    (新增) 项目导出 API
├── services/
│   ├── search_service.py            (新增)
│   ├── token_usage_service.py       (新增)
│   └── export_service.py            (新增)
└── models/
    ├── token_usage.py               (扩展) + project_id, cost_estimate
    └── ai_call.py                   (新增) 完整 AI 调用记录
```

### 2.2 引入的依赖

| 库 | 大小 | 用途 |
|----|------|------|
| Alpine.js 3.x | ~7KB gz | 声明式状态管理（命令面板、模态、状态栏） |
| Fuse.js 7.x | ~12KB gz | 命令面板与全局搜索的模糊匹配 |

均以本地 `static/js/lib/` 形式引入，不走 CDN。

---

## 3 · 各功能详细设计

### 3.1 写作专注（Writing Focus）

#### 3.1.1 自动保存状态指示器

**位置**：全局状态栏最左侧。

**状态机**：

```
idle  ──编辑──>  dirty  ──debounce 2s──>  saving  ──success──>  saved
                                              │
                                              └──error──>  error (toast + 红色状态)
```

**显示**：

| 状态 | 文本 | 颜色 |
|------|------|------|
| idle / saved | `● 已保存 14:32` | success 绿 |
| dirty | `● 未保存` | warning 黄 |
| saving | `○ 保存中...` | text-secondary |
| error | `⚠ 保存失败` | danger 红 |

**实现要点**：
- 现有 writer `_editor.html` 已有 `hx-trigger="changed delay:2s"`，状态变更通过 `htmx:beforeRequest` / `htmx:afterRequest` 事件接管
- 状态由 Alpine.js store `$store.writer.saveState` 管理
- `Cmd+S` 强制立即保存（取消 debounce）

#### 3.1.2 字数统计与目标

**位置**：状态栏中段，仅写作页。

**显示**：`1,234 / 3,000 字` + 4px 高迷你进度条。无目标时仅显示 `1,234 字`。

**目标设置**：
- chapters 表新增字段 `word_target: Integer NULL`
- chapter 表单（新建/编辑）增加「目标字数」输入框
- 用户在编辑器中也可点击字数显示直接修改目标

**统计规则**：去除空白后的字符数（中英混排都按字符算）。

#### 3.1.3 专注模式（Focus Mode）

**触发**：编辑器右上角图标按钮 + `Cmd+.`

**行为**：
- `body[data-focus="on"]` 类设置后：
  - 隐藏 `.nav` 与 writer 侧栏（CSS `display: none`）
  - 编辑器铺满 `min(960px, 100vw - 2rem)` 居中
  - 状态栏保留（位置不变）
- 再次按下退出

**状态保存**：localStorage `novelforge-focus-mode`，跨会话保持。

#### 3.1.4 打字机模式（Typewriter Mode）

**触发**：编辑器右上角图标 + `Cmd+;`

**行为**：
- 编辑器容器获得额外 `padding-top: 40vh; padding-bottom: 40vh`
- 在 `input` 事件中计算光标所在行，调整 `scrollTop` 使该行处于视口中央
- 退出时移除 padding 与滚动绑定

**状态保存**：localStorage `novelforge-typewriter-mode`。

### 3.2 快速导航（Quick Nav）

#### 3.2.1 命令面板（Cmd+K）

**触发**：全局 `Cmd/Ctrl+K`，或顶部 nav 右侧增加 `⌘K` 提示按钮。

**结构**：

```
┌─ Command Palette ────────────────────────────────┐
│ 🔍 搜索一切 · 输入命令...                        │
│ ─────────────────────────────────────────────── │
│ [全部] [命令] [项目] [章节] [设定] [AI 历史]    │  ← Tab 切换
│ ─────────────────────────────────────────────── │
│ 最近                                             │
│   📖 第 12 章 · 命名风暴      5 分钟前           │
│   📋 大纲 · 时间机器          昨天               │
│                                                 │
│ 常用命令                                         │
│   ⚡ 切换专注模式             ⌘.                 │
│   ⚡ 新建项目                                    │
│   ⚡ 跳转到大纲               g o                │
└─────────────────────────────────────────────────┘
```

**数据来源**：
- **命令**：硬编码列表 `app/static/js/palette-commands.js`（动作 + 标签 + 快捷键 + 上下文条件）
- **项目/章节/设定/大纲/灵感**：调用 `/api/search?q=...&type=...`
- **AI 历史**：调用 `/api/ai-history/recent?limit=20`
- **最近访问**：localStorage `novelforge-recent`（最多 20 项，按时间倒序，自动去重）

**键盘交互**：
- `↑↓` 在结果间移动
- `Tab` 切换标签
- `Enter` 选中执行（项目跳转 / 命令调用）
- `Esc` 关闭
- 输入框聚焦时仍可用 `↑↓` 而不移动光标

**搜索算法**：
- Fuse.js 多键模糊：标题（权重 1.0）+ 描述/摘要（权重 0.4）
- 阈值 0.4，最多返回每个标签 5 项
- 空查询时：合并显示「最近 + 常用命令」各 5 条

**实现位置**：`_palette.html` 模板被 `base.html` `{% include %}` 引入，全局可用。

#### 3.2.2 全局快捷键

**完整清单**（注册在 `shortcuts.js`，文档化在帮助模态）：

| 快捷键 | 动作 | 适用范围 |
|--------|------|----------|
| `⌘K` / `Ctrl+K` | 打开命令面板 | 全局 |
| `⌘.` | 切换专注模式 | 写作页 |
| `⌘;` | 切换打字机模式 | 写作页 |
| `⌘S` | 强制立即保存 | 写作页 |
| `⌘/` | 显示快捷键帮助 | 全局 |
| `Esc` | 关闭模态/面板 | 全局 |
| `g p` | 跳转项目列表 | 全局（非输入框聚焦时） |
| `g o` | 跳转当前项目大纲 | 项目内 |
| `g w` | 跳转当前项目写作 | 项目内 |
| `g s` | 跳转当前项目设定集 | 项目内 |
| `g r` | 跳转当前项目审阅 | 项目内 |
| `g i` | 跳转灵感 | 全局 |
| `g b` | 跳转头脑风暴 | 全局 |
| `g h` | 跳转 AI 历史 | 全局 |

**vim-style 跳转**：实现状态机，按下 `g` 后等待 800ms 接收第二个键，期间显示提示。

**冲突处理**：所有快捷键在输入框（textarea/input/contenteditable）聚焦时禁用，除 `⌘K` / `⌘S` / `⌘.` / `⌘;` / `Esc`。

#### 3.2.3 最近访问

**数据**：localStorage，结构：

```json
[
  {"type":"chapter","id":"uuid","title":"第 12 章","project_id":"uuid","ts":1716000000},
  {"type":"outline","id":"uuid","title":"大纲","project_id":"uuid","ts":1716000000}
]
```

**记录时机**：
- 进入写作页（chapter）记录章节
- 进入大纲页记录大纲
- 进入设定详情记录该条设定
- 进入项目详情记录项目

**消费时机**：命令面板空查询时显示前 5 条；专门的「最近」标签显示前 20 条。

#### 3.2.4 面包屑导航

**位置**：在 `.page-header` 上方插入一行（每个页面模板增加），或由 base.html 提供占位 block。

**层级**：

```
项目 › 时间机器 › 大纲 › 第 3 章
```

**实现**：
- base.html 添加 `{% block breadcrumb %}{% endblock %}`
- 各页面定义 breadcrumb 内容
- 抽取公共组件 `_breadcrumb.html`：接收 `crumbs` 列表，每项 `{title, href}`

### 3.3 AI 透明度

#### 3.3.1 Token 用量表盘

**入口**：状态栏右侧 `📊 24.5K` 徽标。点击弹模态。

**模态结构**：

```
┌─ Token 用量 ────────────────────────────────┐
│ [今日] [本周] [本月] [全部]                  │
│ ────────────────────────────────────────── │
│  ┌──────┐ ┌──────┐ ┌──────┐                │
│  │24.5K │ │ 18.2K│ │ 6.3K │                │
│  │ 总计 │ │ 输入 │ │ 输出 │                │
│  └──────┘ └──────┘ └──────┘                │
│                                            │
│ 按场景                                     │
│   写作生成      12.4K  ████████░░          │
│   大纲生成      8.1K   ███████░░░          │
│   头脑风暴      3.0K   ███░░░░░░░          │
│   审阅           1.0K   █░░░░░░░░░         │
│                                            │
│ 按模型                                     │
│   claude-sonnet  20.1K                     │
│   gpt-4-turbo    4.4K                      │
└────────────────────────────────────────────┘
```

**API**：`GET /api/token-usage/summary?period=today|week|month|all`

**响应**：

```json
{
  "total": 24500,
  "input": 18200,
  "output": 6300,
  "by_scenario": {"writing": 12400, "outline_gen": 8100, "brainstorm": 3000, "review": 1000},
  "by_model": {"claude-sonnet-4": 20100, "gpt-4-turbo": 4400}
}
```

**徽标更新**：每次 AI 调用后通过 HX-Trigger 头携带 `tokens-updated` 事件，状态栏监听并刷新。

#### 3.3.2 AI 生成进度可视化

**适用场景**：已使用 SSE 流式响应的端点（章节生成、大纲生成、头脑风暴、审阅）。

**改进**：
- 客户端：将现有「生成中...」替换为：

```
┌─ 正在生成 ──────────────────────────────────┐
│ ░░░░░░░░░░░░░░░░░░░ 1,234 字 · 12s          │
└────────────────────────────────────────────┘
```

- 进度条采用「不确定进度」样式（CSS animation 横向流动，不显示百分比）
- 实时字符数：累加 SSE delta 长度
- 用时：客户端开始时间到现在

**实现**：在 `_editor.html`、`_chat.html` 等流式调用的脚本中接入。

#### 3.3.3 生成前上下文预览

**触发**：所有 AI 生成按钮的 click 改为：先 POST 到 `/api/preview-context`，拿到 context 与 token 估算，再弹模态确认。

**API**：`POST /api/preview-context`

**Request**：

```json
{"scenario": "chapter_writing", "params": {"project_id": "uuid", "chapter_id": "uuid", "sections": [...]}}
```

**Response**：

```json
{
  "context_blocks": [
    {"label": "项目大纲", "content": "...", "tokens": 1200},
    {"label": "相关设定", "content": "...", "tokens": 800},
    {"label": "本章细纲", "content": "...", "tokens": 300}
  ],
  "total_tokens": 2300,
  "estimated_cost_usd": 0.0046,
  "model": "claude-sonnet-4-6"
}
```

**模态**：

```
┌─ 即将调用 AI ──────────────────────────────┐
│ 场景：章节正文生成                          │
│ 模型：claude-sonnet-4-6                    │
│ 预估：2,300 Token  ·  约 $0.0046           │
│                                            │
│ 上下文（可折叠预览）                        │
│   ▸ 项目大纲（1,200 tokens）                │
│   ▸ 相关设定（800 tokens）                  │
│   ▸ 本章细纲（300 tokens）                  │
│                                            │
│              [取消]    [确认生成]           │
└────────────────────────────────────────────┘
```

**用户偏好**：模态可勾选「以后不再预览本场景」，存 localStorage `novelforge-skip-preview-{scenario}`。

**实现**：抽 `context_builder.py` 中已存在的上下文组装逻辑，新增独立路由调用。

#### 3.3.4 AI 调用历史与重跑

**新页面**：`/ai-history`，导航 nav 中不添加链接（避免过度暴露），通过 Cmd+K 和快捷键 `g h` 访问。

**列表**：

```
项目          场景    模型              Token   时间        操作
─────────────────────────────────────────────────────────────
时间机器  章节生成  claude-sonnet-4  2,341   2 分钟前  [查看] [重跑] [diff]
时间机器  大纲生成  claude-sonnet-4  1,820   5 分钟前  [查看] [重跑] [diff]
```

**数据模型**：新增 `ai_call` 表：

```python
class AICall(Base):
    __tablename__ = "ai_call"
    id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=True)
    scenario = Column(String, nullable=False)
    model = Column(String, nullable=False)
    prompt = Column(Text)
    response = Column(Text)
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    duration_ms = Column(Integer)
    status = Column(String)  # success / error
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

**记录时机**：所有 LLM adapter 调用结束时插入。

**操作**：
- **查看**：弹模态展示完整 prompt + response（markdown 渲染）
- **重跑**：用相同 prompt 再调用一次，结果作为新记录
- **diff**：选两条记录，diff 两次响应

**与 TokenUsage 的关系**：AICall 取代 TokenUsage——前者包含后者全部字段加上 prompt/response/duration/status。统计接口从 AICall 聚合得出，无需冗余的聚合表。

### 3.4 数据检索与管理

#### 3.4.1 全局搜索

**入口**：命令面板「全部」/类型标签下输入。

**API**：`GET /api/search?q=keyword&type=all|project|chapter|outline|setting|idea&limit=20`

**实现策略**：
- 当前数据量预期 < 1 万条，使用 SQLite `LIKE '%kw%'` 跨表 UNION 即可
- 服务端返回扁平列表，每项 `{type, id, title, snippet, project_id, project_title}`
- 客户端 Fuse.js 不在前端做模糊（避免拉全表），完全依赖服务端

**示例响应**：

```json
{
  "results": [
    {"type":"chapter","id":"uuid","title":"第 12 章 · 命名风暴","snippet":"...风暴肆虐了三日...","project_id":"uuid","project_title":"时间机器"},
    {"type":"setting","id":"uuid","title":"风暴系魔法","snippet":"...一种典型的元素系魔法...","project_id":"uuid","project_title":"时间机器"}
  ],
  "total": 2
}
```

#### 3.4.2 批量选择与操作

**适用页面**：设定集列表、章节列表、灵感列表、大纲项列表。

**触发**：每个列表项左侧 hover 时出现 checkbox。任何 checkbox 选中后，顶部出现操作条：

```
┌────────────────────────────────────────────┐
│ 已选 3 项   [删除] [移到分组▾] [取消]      │
└────────────────────────────────────────────┘
```

**实现**：通用 `bulk-select.js`（Alpine.js 组件），任何列表加 `x-data="bulkSelect()"` 即可启用。批量操作通过 HTMX 提交，端点形如 `POST /project/{id}/settings/bulk-delete` 接收 `ids: [...]`。

**键盘辅助**：Shift+Click 区间选择，Cmd/Ctrl+A 全选当前可见。

#### 3.4.3 列表项内联重命名

**触发**：列表项标题右侧的 ✎ 图标（默认低亮，hover 时高亮）。

**行为**：
- 点击 ✎ → 标题变为 `<input>`，自动聚焦并 select 全文
- `Enter` → PATCH 到对应端点（如 `PATCH /api/settings/{id}` `{title: "..."}`）
- `Esc` → 取消，恢复原标题
- 失焦也视为提交

**实现**：通用 `inline-rename.js`，HTML 形如：

```html
<span class="inline-rename" data-rename-endpoint="/api/settings/{id}">
  <span class="title">原标题</span>
  <button class="rename-icon">✎</button>
</span>
```

#### 3.4.4 项目导出/备份

**入口**：项目详情页页头按钮 `📦 导出`。

**模态**：

```
┌─ 导出项目 ─────────────────────────────────┐
│ ○ 完整 JSON（包含全部实体，用于备份/迁移）  │
│ ○ 故事 Markdown（章节正文，按大纲拼装）      │
│ ○ 大纲 + 设定 Markdown（创作笔记）          │
│                                            │
│        [取消]    [下载]                     │
└────────────────────────────────────────────┘
```

**API**：`GET /api/export/{project_id}?format=json|story_md|notes_md`

**响应**：直接返回文件流，`Content-Disposition: attachment; filename="..."`。

**导入**（未来扩展，本期不实现）：占位 endpoint 注释。

---

## 4 · 数据模型变更

### 4.1 新增表

**`ai_call`**（替代 token_usage）：

```sql
CREATE TABLE ai_call (
    id TEXT PRIMARY KEY,
    project_id TEXT REFERENCES projects(id),
    scenario TEXT NOT NULL,
    model TEXT NOT NULL,
    prompt TEXT,
    response TEXT,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    duration_ms INTEGER,
    status TEXT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ai_call_created ON ai_call(created_at DESC);
CREATE INDEX ai_call_scenario ON ai_call(scenario);
CREATE INDEX ai_call_project ON ai_call(project_id);
```

**迁移**：
- 在 `init_db()` 中创建新表
- 一次性迁移：从 `token_usage` 把历史记录复制到 `ai_call`（prompt/response/duration_ms/error_message 留空，status 置 `success`，scenario/model/tokens/created_at 直接迁移）
- 迁移完成后立即 `DROP TABLE token_usage`，删除 `app/models/token_usage.py`
- 所有 adapter 调用改写为只写 `ai_call`（不再双写）

### 4.2 已有表扩展

**`chapters`**：新增 `word_target INTEGER NULL`。

---

## 5 · API 端点清单

| 方法 | 路径 | 用途 |
|------|------|------|
| GET | `/api/search` | 全局搜索 |
| GET | `/api/token-usage/summary` | Token 用量聚合 |
| GET | `/api/ai-history` | AI 调用历史列表 |
| GET | `/api/ai-history/{id}` | 单条详情 |
| POST | `/api/ai-history/{id}/rerun` | 重跑 |
| POST | `/api/preview-context` | AI 调用前上下文预览 |
| GET | `/api/export/{project_id}` | 导出 |
| POST | `/api/projects/bulk-delete` | 批量删除项目 |
| POST | `/project/{pid}/settings/bulk-delete` | 批量删除设定 |
| POST | `/project/{pid}/chapters/bulk-delete` | 批量删除章节 |
| POST | `/api/ideas/bulk-delete` | 批量删除灵感 |
| PATCH | `/api/settings/{id}` | 内联重命名（其他实体同形） |

---

## 6 · 错误处理

- **状态栏「保存失败」**：保留现有 toast，并把状态栏切到红色 `⚠ 保存失败`，点击重试
- **命令面板搜索失败**：显示 inline `搜索暂不可用，请稍后`
- **AI 上下文预览接口失败**：toast「预览失败，仍可直接生成」，按钮变为「跳过预览生成」
- **Token 用量加载失败**：状态栏徽标显示 `📊 --`，hover 显示原因
- **导出失败**：toast + 模态内显示错误信息

所有错误统一走现有 `htmx:responseError` 处理器扩展。

---

## 7 · 测试策略

### 7.1 单元测试

- `search_service`：覆盖各实体类型与边界（空查询、特殊字符、SQL 注入测试）
- `token_usage_service.summary`：聚合的 period 边界
- `export_service`：每种格式的输出结构

### 7.2 集成测试（pytest + httpx）

- 全局搜索端点：构造 5 类实体的数据集，验证返回
- AI 调用记录写入：模拟 LLM 调用，验证 `ai_call` 表写入
- 上下文预览：固定项目数据，验证 token 估算稳定

### 7.3 手工 UX 验证

每个交付阶段结束后：

- [ ] Cmd+K 在每个主要页面都能唤起
- [ ] 全部快捷键可触发对应动作
- [ ] 写作页：自动保存 / 字数 / 专注 / 打字机 四种状态切换无冲突
- [ ] AI 生成前预览，确认后正常生成
- [ ] Token 表盘数字与实际调用记录一致
- [ ] 批量选择 + 删除：选择→删除→列表更新
- [ ] 内联重命名：Enter 保存、Esc 取消、失焦保存
- [ ] 项目导出：3 种格式都能下载并正确解析

---

## 8 · 与现有代码的关系

### 8.1 复用

- 现有 toast 系统、HTMX 加载指示器、深浅主题切换
- `context_builder.py` 直接复用为预览接口
- 现有 LLM adapter 改造：调用结束写 `ai_call` 表，同时移除原 `token_usage` 写入（一次性切换，见 §4.1 迁移）

### 8.2 替换

- 写作页 `_editor.html` 中的 `placeholder = '正在生成...'` 文本替换为新的进度组件
- 头脑风暴 `_chat.html` 中的 loading 同理
- 各页面顶部 `page-header` 上方加面包屑 block

### 8.3 不动

- 现有路由 URL 全部保留
- 现有 base.html 主题 / 字体 / 导航结构不变（仅在 body 底部新增状态栏 include）
- 现有 Tailwind CDN 不替换（与本地 Alpine.js 并存）

---

## 9 · 阶段建议（供实施计划参考）

按依赖与价值排序（实施计划负责最终切分）：

**P0 · 基础**
- 引入 Alpine.js / Fuse.js，挂载 `/static`
- 新建 `ai_call` 表与服务
- 顶部 nav 增加 `⌘K` 提示

**P1 · 核心入口**
- 命令面板（命令 + 项目跳转 + 最近）
- 全局快捷键
- 面包屑（base.html block + 各页面填充）

**P2 · 写作专注**
- 全局状态栏框架
- 自动保存状态
- 字数统计与目标
- 专注 / 打字机模式

**P3 · AI 透明度**
- Token 表盘（徽标 + 模态）
- 生成进度可视化
- 上下文预览模态
- AI 历史页面

**P4 · 数据管理**
- 全局搜索接入命令面板
- 内联重命名（在最常用列表上线）
- 批量选择（同上）
- 项目导出

每个阶段独立可发布，互不阻塞。
