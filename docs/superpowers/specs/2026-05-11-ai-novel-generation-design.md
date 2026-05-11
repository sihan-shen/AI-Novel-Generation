# AI Novel Generation Tool — 设计规格文档

> 版本：v1.0  
> 日期：2026-05-11  
> 状态：规划完成，待实现

---

## 1. 项目概述

基于 LLM 的小说创作辅助工具，以**结构化创作工作台**为核心设计理念，围绕"小说项目"组织所有功能模块。五大核心功能——大纲/细纲管理、设定集管理、头脑风暴、文风参考、自动审阅——深度集成而非孤立工具。

### 设计原则

| 原则 | 说明 |
|------|------|
| 以项目为中心 | 每个小说是一个 Project，所有数据归属于项目 |
| 结构化数据 | 大纲有层级、设定有字段、章节有元数据，而非纯文本 |
| 上下文感知 | LLM 调用时自动携带相关设定、大纲、前文作为上下文 |
| 模块化 | 五个功能模块通过 LLM 层和 Data 层连接，但可独立使用 |
| 人类在环 | AI 辅助而非替代，所有生成内容需经用户确认 |

---

## 2. 技术栈

| 层 | 技术选型 |
|----|----------|
| 后端框架 | **FastAPI** (Python 3.11+) |
| 前端模板 | **Jinja2** + **HTMX** (交互式 SPA 体验，无需 Node.js) |
| 前端样式 | Tailwind CSS (通过 CDN 或编译版本) |
| 数据库 | **SQLite** (通过 SQLAlchemy ORM) |
| LLM API | Claude API / OpenAI API (可切换，可扩展) |
| 异步任务 | FastAPI Background Tasks + 可选 Celery |
| 依赖管理 | Poetry 或 pip + venv |

### 选型理由

- **FastAPI**：异步支持好、自动文档生成、类型安全，对接 LLM API 时 async/await 优势明显
- **Jinja2 + HTMX**：保留 Python 全栈的简洁性，HTMX 提供足够的交互能力（局部刷新、表单提交、实时更新），无需编写 JS 框架代码
- **SQLite**：单用户本地应用的最佳选择，零运维；future 如需多用户可平滑迁移到 PostgreSQL
- **SQLAlchemy**：ORM 层让数据模型变更可追溯，迁移方便

---

## 3. 整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Web Browser (用户界面)                        │
│        Jinja2 模板 + HTMX 交互 + 半自动 Tailwind CSS 样式            │
└─────────────────────────┬───────────────────────────────────────────┘
                          │ HTTP (SSR + HTMX 局部更新)
┌─────────────────────────▼───────────────────────────────────────────┐
│                      FastAPI Web 层                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │ 路由/Serve │  │ 认证(可选)│  │ 会话管理  │  │ 错误处理  │           │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘           │
└─────────────────────────┬───────────────────────────────────────────┘
                          │ 调用 Service 层
┌─────────────────────────▼───────────────────────────────────────────┐
│                      Service 层 (业务逻辑)                           │
│                                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │ Project   │  │ Outline   │  │ Setting  │  │ Chapter  │           │
│  │ Service   │  │ Service   │  │ Service  │  │ Service  │           │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                          │
│  │ Style     │  │ Review    │  │ Brain-   │                          │
│  │ Service   │  │ Service   │  │ storm    │                          │
│  │           │  │           │  │ Service  │                          │
│  └──────────┘  └──────────┘  └──────────┘                          │
└─────────────────────────┬───────────────────────────────────────────┘
                          │ 调用 LLM 和 DB
┌─────────────────────────▼───────────────────────────────────────────┐
│                      LLM Integration Layer                           │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ 上下文组装器   │  │ Prompt 模板  │  │ API 适配器    │              │
│  │ Context      │  │ Template     │  │ (Claude/     │              │
│  │ Builder      │  │ Manager      │  │  OpenAI/... ) │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
│  ┌──────────────┐  ┌──────────────┐                                 │
│  │ 响应后处理器   │  │ Token 管理器  │                                 │
│  │ Post-        │  │ Usage        │                                 │
│  │ Processor    │  │ Tracker      │                                 │
│  └──────────────┘  └──────────────┘                                 │
└─────────────────────────┬───────────────────────────────────────────┘
                          │ SQLAlchemy ORM
┌─────────────────────────▼───────────────────────────────────────────┐
│                      Data Layer (SQLite)                             │
│                                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │ projects  │  │ outlines  │  │ settings  │  │ chapters  │           │
│  │ (项目)    │  │ (大纲)    │  │ (设定集)  │  │ (章节)    │           │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │ styles    │  │ reviews   │  │ ideas    │  │ relations  │           │
│  │ (文风)    │  │ (审阅)    │  │ (灵感)   │  │ (关联)    │           │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘           │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. 数据模型

### 4.1 核心实体关系

```
Project 1──N Outline
Project 1──N Setting
Project 1──N Chapter
Project 1──N Style
Project 1──N Idea
Project 1──N Review

Setting N──M Setting  (自引用，通过 relations 表)
Outline ──→ Setting   (通过外键关联)
Chapter  ──→ Setting   (通过外键关联)
```

### 4.2 表结构

```sql
-- 项目表
CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    genre TEXT,              -- 小说类型
    status TEXT DEFAULT 'active',  -- active / archived
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 大纲条目表（多态层级：卷/章/节）
CREATE TABLE outlines (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    parent_id TEXT REFERENCES outlines(id),  -- 父级大纲条目
    level INTEGER NOT NULL,                  -- 1=卷, 2=章, 3=节
    sort_order INTEGER NOT NULL,             -- 同层排序
    title TEXT NOT NULL,
    summary TEXT,                            -- 概要/内容描述
    notes TEXT,                              -- 写作说明/备忘
    status TEXT DEFAULT 'draft',             -- draft / writing / done
    word_count_target INTEGER,               -- 字数目标(节/章级)
    word_count_actual INTEGER DEFAULT 0,
    pov_character TEXT,                      -- POV 角色
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 设定条目表
CREATE TABLE settings (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    category TEXT NOT NULL,                   -- 世界观/人物/组织/地理/体系/事件/物品/自定义
    name TEXT NOT NULL,
    summary TEXT,                             -- 一行概要（LLM 快速索引用）
    content TEXT,                             -- 详细描述 (Markdown)
    structured_data JSON,                     -- 结构化字段
    weight INTEGER DEFAULT 5,                 -- 重要度权重 1-10
    sort_order INTEGER DEFAULT 0,             -- 排序
    key TEXT,                                 -- 唯一 key，供 LLM 引用
    status TEXT DEFAULT 'active',             -- active / pending / deprecated
    version INTEGER DEFAULT 1,
    tags TEXT,                                -- JSON array
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 设定关联表（多对多自引用）
CREATE TABLE setting_relations (
    id TEXT PRIMARY KEY,
    from_setting_id TEXT NOT NULL REFERENCES settings(id) ON DELETE CASCADE,
    to_setting_id TEXT NOT NULL REFERENCES settings(id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL,              -- 属于/敌对/位于/涉及/持有者/自定义
    description TEXT,
    UNIQUE(from_setting_id, to_setting_id, relation_type)
);

-- 章节正文表
CREATE TABLE chapters (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    outline_id TEXT REFERENCES outlines(id),  -- 关联的细纲节点
    title TEXT NOT NULL,
    content TEXT,                              -- 正文 Markdown
    sort_order INTEGER NOT NULL,
    status TEXT DEFAULT 'draft',               -- draft / reviewing / done
    word_count INTEGER DEFAULT 0,
    notes TEXT,                                -- 写作批注
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 章节-设定关联表
CREATE TABLE chapter_setting_links (
    chapter_id TEXT NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
    setting_id TEXT NOT NULL REFERENCES settings(id) ON DELETE CASCADE,
    PRIMARY KEY (chapter_id, setting_id)
);

-- 大纲-设定关联表
CREATE TABLE outline_setting_links (
    outline_id TEXT NOT NULL REFERENCES outlines(id) ON DELETE CASCADE,
    setting_id TEXT NOT NULL REFERENCES settings(id) ON DELETE CASCADE,
    PRIMARY KEY (outline_id, setting_id)
);

-- 文风格表
CREATE TABLE styles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    source TEXT,                               -- 来源描述
    source_text TEXT,                          -- 参考原文节选
    analysis JSON,                             -- LLM 文风分析结果
    tags TEXT,                                 -- JSON array
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 项目-文风关联表
CREATE TABLE project_style_links (
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    style_id TEXT NOT NULL REFERENCES styles(id) ON DELETE CASCADE,
    weight REAL DEFAULT 1.0,                   -- 混合权重
    PRIMARY KEY (project_id, style_id)
);

-- 审阅报告表
CREATE TABLE reviews (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    chapter_id TEXT REFERENCES chapters(id),  -- 可为空（批量审阅）
    scope TEXT NOT NULL,                       -- instant / batch / diff
    summary JSON,                              -- 综合评分与摘要
    findings JSON,                             -- 审阅条目列表
    status TEXT DEFAULT 'pending',             -- pending / reviewing / resolved
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 灵感便签表
CREATE TABLE ideas (
    id TEXT PRIMARY KEY,
    project_id TEXT REFERENCES projects(id),   -- 可为空（跨项目灵感）
    title TEXT,
    content TEXT,
    source TEXT,                                -- 手写 / brainstorm
    tags TEXT,                                  -- JSON array
    status TEXT DEFAULT 'active',               -- active / promoted / discarded
    promoted_to_type TEXT,                      -- setting / outline / chapter
    promoted_to_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 5. 模块详细设计

### 5.1 大纲/细纲管理

**四层结构**：卷 → 章 → 节 → 场景要点。支持四种视图：

| 视图 | 用途 |
|------|------|
| 树状视图（默认） | 卷→章→节层级展开，拖拽排序 |
| 时间线视图 | 按故事时间轴展示，检查时间线一致性 |
| POV 视图 | 按角色视角筛选章节 |
| 进度视图 | 甘特图风格进度展示 |

**大纲分析功能**（LLM 驱动）：
- 节奏分析：各章节内容密度、冲突分布
- 伏笔检查：前文伏笔是否回收
- 缺失检测：大纲中是否存在断层

### 5.2 设定集管理

**结构化条目**：每个设定条目包含 category、name、summary、content（Markdown）、structured_data（JSON）、relations、tags、status、version。

**关系图谱**：通过 setting_relations 表构建设定间的关联网络。LLM 上下文打包时沿关系链自动拉取相关设定。

**LLM 可读性**：生成特殊格式的设定摘要供 LLM 引用，包含权重标记、唯一 key、结构化字段。

**三层打扫机制**：

| 层级 | 方式 | 触发 |
|------|------|------|
| 基础清扫 | 孤立检测、空条目检测、版本清理 | 每次保存自动触发 |
| 一致性检查 | LLM 驱动矛盾检测、重复检测 | 定时（可配置）或手动 |
| 深度清理 | 全面审查、归档废弃、关系补全 | 用户手动触发 |

### 5.3 头脑风暴

**三种启动模式**：
- 自由发散：任意问题 → LLM 自由联想
- 上下文风暴：基于当前编辑内容展开创意延伸
- 定向激荡：指定方向（人物发展、情节分支、设定扩展、冲突设计）

**发散→收敛→沉淀流程**：LLM 生成多个创意 → 用户圈选 → LLM 深化 → 沉淀到设定集/大纲/便签。

**灵感便签**：轻量记录零散想法，可标签化、可升级为正式条目。

### 5.4 参考文风

**文风条目**：包含来源文本、LLM 自动分析结果（词汇特征、节奏、修辞、语气、对话风格、叙事视角）。

**智能导入**：用户粘贴长文本 → LLM 分析切片（检测风格变化、提取特征段落）→ 用户审批确认 → LLM 深度分析 → 存入文风库。

**三级应用**：
1. 指令注入：最轻量
2. 参考示例注入：更准确
3. 风格持续跟踪：写作中持续匹配度检测与反馈

**文风混合**：多文风按权重融合。**文风检测**：分析当前正文，进行一致性评分和调整建议。

### 5.5 自动审阅

**五维审阅引擎**：

| 维度 | 检查项 |
|------|--------|
| 设定一致性 | 设定违背、设定遗漏、命名错误 |
| 文风一致性 | 风格漂移、语调失调、POV 违规（双重基准：目标文风 + 前文实际文风） |
| 逻辑与结构 | 情节逻辑、时间线、节奏异常、伏笔回收 |
| 语言润色 | 语病、用词、对话、感官缺失 |
| 综合评估 | 可读性评分、各维度评分、改进优先级 |

**三种模式**：即时审阅（轻量实时）、批量审阅（全量报告）、差异审阅（增量检查）。

**修复方式**：批量修复（LLM 一次生成）、逐项修复（手动定位）、智能修复（diff 对比确认）。

---

## 6. LLM 集成层设计

### 6.1 上下文组装器 (Context Builder)

```
请求进入 → 识别场景 → 收集相关数据 → 组装为结构化上下文
                                                         │
场景类型：                   收集内容：
├─ 写作辅助                  ├─ 设定集（关联条目 + 关系链扩展）
├─ 头脑风暴                  ├─ 大纲（当前层级 + 上下级 + 同级）
├─ 文风分析                  ├─ 前文（最近 N 章 + 当前章节）
├─ 审阅                      ├─ 文风（目标文风 + 前文文风特征）
└─ 打扫                      ├─ 历史审阅记录
                              └─ 当前用户指令（Prompt）
```

### 6.2 Prompt 模板管理器

每个场景有专门的模板，模板核心结构：

```
=== SYSTEM ===
你是小说创作助手。你的任务是辅助而非替代。

=== PROJECT CONTEXT ===
项目类型: {genre}
当前进度: {progress}

=== SETTINGS ===
{设定集摘要 — 仅活跃条目}

=== STYLE REFERENCE ===
{目标文风特征}

=== CURRENT FOCUS ===
{当前正在编辑的内容}

=== REQUEST ===
{用户的具体请求}
```

### 6.3 API 适配器

```
LLMAdapter (抽象基类)
├── ClaudeAdapter    (Anthropic SDK)
├── OpenAIAdapter    (OpenAI SDK)
└── CustomAdapter    (用户自定义端点)

每个适配器实现：
  - generate(messages, config) → Response
  - count_tokens(text) → int
```

### 6.4 响应后处理器

- 提取结构化数据（如文风分析 JSON）
- 格式化 Markdown 输出
- 设定引用关系识别与回写
- Token 用量记录

---

## 7. 页面路由与交互

| 路由 | 页面 | 功能概要 |
|------|------|----------|
| `/` | 仪表盘 | 项目列表、创建新项目、全局灵感板 |
| `/project/{id}` | 项目工作台 | 项目概览、快捷入口、写作进度 |
| `/project/{id}/outline` | 大纲编辑器 | 树状大纲、拖拽排序、关联设定 |
| `/project/{id}/settings` | 设定集 | 分类浏览、关系图谱、打扫面板 |
| `/project/{id}/settings/{sid}` | 设定详情 | 编辑、关联查看、版本历史 |
| `/project/{id}/writer` | 写作编辑器 | 章节写作、侧边栏参考（设定+大纲） |
| `/project/{id}/writer/{ch}` | 章节编辑 | 正文编辑、即时审阅、文风检查 |
| `/project/{id}/review` | 审阅面板 | 审阅报告列表、逐项处理 |
| `/project/{id}/review/new` | 发起审阅 | 选择范围/维度/模式 |
| `/styles` | 文风库 | 文风条目管理、智能导入 |
| `/brainstorm` | 头脑风暴 | 三种启动模式 + 灵感便签 |

交互以 HTMX 驱动：表单提交、内容加载、列表刷新等均为局部更新，无需整页刷新。

---

## 8. 开发阶段规划

### Phase 1 — 基础骨架 (Week 1-2)
- [ ] FastAPI 项目初始化 + 项目结构
- [ ] SQLAlchemy 数据模型定义 + 迁移
- [ ] 基础页面路由 + Jinja2 布局
- [ ] LLM API 适配器（Claude）
- [ ] 项目管理 CRUD

### Phase 2 — 核心创作 (Week 3-4)
- [ ] 大纲管理器（树状视图、CRUD、拖拽排序）
- [ ] 设定集管理器（分类浏览、条目 CRUD、关系绑定）
- [ ] 写作编辑器（章节管理、Markdown 编辑）
- [ ] 设定关联 UI（在章节/大纲中绑定设定）

### Phase 3 — AI 功能 (Week 5-6)
- [ ] 上下文组装器 + Prompt 模板
- [ ] 头脑风暴（三种模式）
- [ ] 文风导入与分析（智能切片 + 审批）
- [ ] 文风应用（写作时风格引导）

### Phase 4 — 审阅与打扫 (Week 7-8)
- [ ] 自动审阅引擎（五维检查）
- [ ] 审阅报告 UI
- [ ] 批量修复 / 逐项修复
- [ ] 设定集打扫机制（三层）

### Phase 5 — 打磨 (Week 9-10)
- [ ] 差异化审阅
- [ ] 文风混合与检测
- [ ] 灵感便签系统
- [ ] 性能优化与 Token 管理

---

## 9. 注意点与约束

1. **Token 管理**：所有 LLM 调用需要记录 token 消耗，上下文组装器应尽量压缩无用信息
2. **错误容忍**：LLM 调用可能失败（网络/限流），所有 AI 功能应有降级方案和用户提示
3. **数据安全**：设定和章节内容存储在本地 SQLite，不上传到第三方。用户可配置 API key
4. **可扩展模型**：适配器模式使切换/增加 LLM 提供商无需修改业务代码
5. **异步优先**：LLM 调用是 IO 密集型，所有涉及 LLM 的接口应使用异步处理，避免阻塞

---

## 10. 目录结构建议

```
ai-novel-generation/
├── app/
│   ├── main.py                 # FastAPI 入口
│   ├── config.py               # 配置管理（API key 等）
│   ├── database.py             # 数据库连接 + 会话
│   ├── models/                 # SQLAlchemy 模型
│   │   ├── __init__.py
│   │   ├── project.py
│   │   ├── outline.py
│   │   ├── setting.py
│   │   ├── chapter.py
│   │   ├── style.py
│   │   ├── review.py
│   │   └── idea.py
│   ├── schemas/                # Pydantic 校验/序列化
│   │   ├── __init__.py
│   │   └── ...
│   ├── services/               # 业务逻辑
│   │   ├── __init__.py
│   │   ├── project_service.py
│   │   ├── outline_service.py
│   │   ├── setting_service.py
│   │   ├── chapter_service.py
│   │   ├── style_service.py
│   │   ├── review_service.py
│   │   └── brainstorm_service.py
│   ├── llm/                    # LLM 集成层
│   │   ├── __init__.py
│   │   ├── adapter.py          # 抽象适配器
│   │   ├── claude_adapter.py
│   │   ├── openai_adapter.py
│   │   ├── context_builder.py  # 上下文组装
│   │   ├── templates/          # Prompt 模板
│   │   │   ├── brainstorm.yaml
│   │   │   ├── writing.yaml
│   │   │   ├── review.yaml
│   │   │   ├── style_analysis.yaml
│   │   │   └── cleaning.yaml
│   │   └── post_processor.py   # 响应后处理
│   ├── routers/                # FastAPI 路由
│   │   ├── __init__.py
│   │   ├── projects.py
│   │   ├── outlines.py
│   │   ├── settings.py
│   │   ├── chapters.py
│   │   ├── styles.py
│   │   ├── reviews.py
│   │   └── brainstorming.py
│   └── templates/              # Jinja2 模板
│       ├── base.html
│       ├── dashboard.html
│       ├── project/
│       ├── outline/
│       ├── settings/
│       ├── writer/
│       ├── review/
│       ├── styles/
│       └── brainstorm/
├── docs/
│   └── superpowers/
│       └── specs/
│           └── 2026-05-11-ai-novel-generation-design.md
├── requirements.txt
├── pyproject.toml              # 或 setup.py
└── README.md
```
