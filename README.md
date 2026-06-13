# Novel Forge — AI 辅助小说创作工具

基于 LLM 的小说创作辅助工具。围绕创作流程设计，提供大纲管理、设定集维护、Agent 对话、文风参考、自动审阅五大核心功能。

## 功能概览

```
项目工作台 ─┬─ 大纲/细纲管理 ── 三层树状结构（卷→章→节）
            │                  ├─ 关联设定集（设定引用追踪）
            │                  └─ LLM 大纲生成
            │
            ├─ 设定集管理 ──── 结构化条目（人物/世界观/组织/地理/体系/事件/物品）
            │                  ├─ 关系图谱（设定间逻辑关联）
            │                  ├─ LLM 可读格式（自动摘要 + 权重标记 + 唯一 key）
            │                  └─ 三层打扫机制（孤立检测 / LLM 矛盾扫描 / 深度归档）
            │
            ├─ Agent 对话 ──── 智能写作助手
            │                  ├─ 自由脑暴 / 定向激荡 / 上下文风暴
            │                  ├─ LLM 驱动创意生成
            │                  └─ 流式 SSE 实时响应
            │
            ├─ 参考文风 ────── 文风库管理（LLM 自动分析）
            │                  ├─ 智能切片导入（长文本 → LLM 切片 → 用户审批）
            │                  └─ 文风混合（项目多文风权重配置）
            │
            └─ 自动审阅 ────── LLM 四维审阅（设定/文风/逻辑/语言）
                               └─ 批量审阅 + 差异审阅
```

## 技术栈

| 层 | 技术 |
|----|------|
| 后端框架 | **FastAPI** (Python 3.11+) |
| 前端框架 | **Next.js 16** (App Router, TypeScript) |
| UI 组件 | **shadcn/ui** (Base UI + Tailwind CSS v4) |
| 状态管理 | **Zustand** + **TanStack Query** |
| HTTP 客户端 | **ky** |
| 类型生成 | **openapi-typescript** (FastAPI → TypeScript) |
| 数据库 | **SQLite** (SQLAlchemy ORM) |
| LLM API | Claude API / OpenAI API（可切换） |

## 快速开始

### 前置要求

- Python 3.11+
- Node.js 22+
- 一个 LLM API Key（Claude 或 OpenAI）

### 启动

```bash
# 克隆仓库
git clone <url> ai-novel-generation
cd ai-novel-generation

# —— 后端 ——
python -m venv .venv
source .venv/bin/activate
pip install -e .

# 配置 API Key
cp .env.example .env
# 编辑 .env，填入你的 CLAUDE_API_KEY 或 OPENAI_API_KEY

# 启动后端（数据库自动初始化）
uvicorn app.main:app --reload --port 8000

# —— 前端（另一个终端）——
cd novel-frontend
npm install
npm run dev

# 或一键同时启动：
./dev.sh
```

### 访问

| 地址 | 说明 |
|------|------|
| http://localhost:3000 | Next.js 前端 |
| http://localhost:8000 | FastAPI API 根 |
| http://localhost:8000/docs | Swagger API 文档 |
| http://localhost:8000/openapi.json | OpenAPI spec |

## 项目结构

```
ai-novel-generation/
├── app/                          # FastAPI 后端
│   ├── main.py                   # 入口 + 路由注册 + CORS
│   ├── config.py                 # 环境配置（API Key 等）
│   ├── database.py               # SQLAlchemy 引擎 + init_db()
│   ├── models/                   # ORM 模型（11 表）
│   ├── schemas/                  # Pydantic 校验 + 响应
│   ├── services/                 # 业务逻辑层
│   ├── llm/                      # LLM 集成（Claude / OpenAI）
│   │   ├── adapter.py            # 抽象基类 + 工厂
│   │   ├── claude_adapter.py
│   │   ├── openai_adapter.py
│   │   └── templates/            # YAML 提示词模板
│   ├── routers/                  # JSON API 路由（纯 JSON，无 HTML）
│   ├── agents/                   # Agent 系统（脑暴 / 写作）
│   └── migrations/               # 数据库迁移
│
├── novel-frontend/               # Next.js 前端
│   ├── src/
│   │   ├── app/                  # App Router 页面
│   │   ├── components/
│   │   │   ├── ui/               # shadcn/ui 组件
│   │   │   ├── layout/           # 侧栏、导航等
│   │   │   └── features/         # 业务组件
│   │   ├── lib/
│   │   │   ├── api-client.ts     # ky HTTP 客户端
│   │   │   ├── query-provider.tsx # TanStack Query 提供者
│   │   │   └── queries/          # 各资源 TanStack Query hooks
│   │   ├── stores/               # Zustand stores
│   │   ├── hooks/                # 自定义 hooks（SSE 等）
│   │   └── types/                # openapi-typescript 自动生成类型
│   ├── next.config.ts            # API rewrites → localhost:8000
│   └── package.json
│
├── tests/                        # pytest 测试
│   ├── conftest.py               # 测试夹具（SQLite 内存数据库）
│   └── test_api_*.py             # 各资源 JSON API 测试
├── dev.sh                        # 一键启动前后端
├── pyproject.toml
└── README.md
```

## 页面路由

| 路由 | 页面 |
|------|------|
| `/` | 工作台入口 |
| `/projects` | 项目列表（新建 + 删除） |
| `/projects/[id]` | 项目详情（功能入口） |
| `/projects/[id]/outline` | 大纲树（递归展示 + 编辑） |
| `/projects/[id]/settings` | 设定集（分类筛选 + CRUD） |
| `/projects/[id]/writer` | 章节写作编辑器 |
| `/projects/[id]/agent` | Agent 对话助手（SSE 流式） |
| `/projects/[id]/review` | 审阅面板 |
| `/ideas` | 灵感快速记录 |
| `/styles` | 文风库管理 |
| `/config` | LLM 和服务器配置 |

## API 端点

后端暴露了 20+ JSON API 端点（OpenAPI spec 自动同步到前端类型）：

| 资源 | 端点 |
|------|------|
| Projects | `GET/POST /api/projects`, `GET/DELETE /api/projects/{id}` |
| Outlines | `GET/POST /api/projects/{pid}/outlines`, `GET/PUT/DELETE /{oid}` |
| Settings | `GET/POST /api/projects/{pid}/settings`, `GET/PUT/DELETE /{sid}` |
| Chapters | `GET/POST /api/projects/{pid}/chapters`, `GET/PUT/DELETE /{cid}` |
| Styles | `GET/DELETE /api/styles` |
| Ideas | `GET/POST /api/ideas`, `DELETE /{id}` |
| Reviews | `GET /api/projects/{pid}/reviews`, `GET /{rid}` |
| Config | `GET/POST /api/config` |

所有端点返回统一格式：`{"data": ..., "message": "ok"}`。

## 测试

```bash
# 运行后端测试（全量）
pytest tests/

# 运行特定测试
pytest tests/test_api_projects.py -v

# 生成前端类型（需要后端运行中）
cd novel-frontend && npm run gen:types
```

## 测试

```bash
# 后端测试
pytest tests/        # 108 tests

# 前端类型检查
cd novel-frontend && npm run build  # 12 routes
```

## License

MIT
