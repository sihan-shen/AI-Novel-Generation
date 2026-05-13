# AI Novel Generation Tool

基于 LLM 的小说创作辅助工具。围绕创作流程设计，提供大纲管理、设定集维护、头脑风暴、文风参考、自动审阅五大核心功能。

## 功能概览

```
项目工作台 ─┬─ 大纲/细纲管理 ── 三层树状结构（卷→章→节）
            │                  ├─ 关联设定集（设定引用追踪）
            │                  └─ LLM 大纲分析
            │
            ├─ 设定集管理 ──── 结构化条目（人物/世界观/组织/地理/体系/事件/物品）
            │                  ├─ 关系图谱（设定间逻辑关联）
            │                  ├─ LLM 可读格式（自动摘要 + 权重标记 + 唯一 key）
            │                  └─ 三层打扫机制（孤立检测 / LLM 矛盾扫描 / 深度归档）
            │
            ├─ 头脑风暴 ────── 自由发散 / 上下文风暴 / 定向激荡
            │                  └─ LLM 驱动创意生成
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
| 前端模板 | **Jinja2** + **HTMX** |
| 样式 | Tailwind CSS (CDN) |
| 数据库 | **SQLite** (SQLAlchemy ORM) |
| LLM API | Claude API / OpenAI API（可切换） |

## 快速开始

```bash
# 进入项目目录
cd ai-novel-generation

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install fastapi uvicorn sqlalchemy jinja2 anthropic openai \
            python-multipart aiofiles pydantic-settings pyyaml

# 配置 API Key（LLM 功能需要）
cp .env.example .env
# 编辑 .env，填入你的 CLAUDE_API_KEY

# 启动服务（数据库自动初始化）
uvicorn app.main:app --reload --port 8000

# 打开浏览器访问 http://localhost:8000
```

## 项目结构

```
ai-novel-generation/
├── app/
│   ├── main.py                 # FastAPI 入口 + 路由注册
│   ├── config.py               # 配置（API Key 等）
│   ├── database.py             # SQLAlchemy 引擎 + init_db()
│   ├── models/                 # ORM 模型（11 张表）
│   │   ├── project.py, outline.py, setting.py
│   │   ├── chapter.py, style.py, review.py
│   │   ├── idea.py, token_usage.py
│   ├── schemas/                # Pydantic 校验
│   │   ├── project.py, outline.py, setting.py, chapter.py
│   ├── services/               # 业务逻辑层
│   │   ├── project_service.py, outline_service.py
│   │   ├── setting_service.py, chapter_service.py
│   │   ├── style_service.py, review_service.py
│   │   ├── brainstorm_service.py
│   │   ├── cleaning_service.py, idea_service.py
│   ├── llm/                    # LLM 集成层
│   │   ├── adapter.py          # 抽象基类 + 工厂
│   │   ├── claude_adapter.py, openai_adapter.py
│   │   ├── context_builder.py  # 场景上下文组装
│   │   └── templates/          # YAML 提示词模板
│   │       ├── writing.yaml, brainstorm.yaml, review.yaml
│   │       ├── style_analysis.yaml, cleaning.yaml
│   ├── routers/                # API 路由
│   │   ├── projects.py, outlines.py, settings.py
│   │   ├── chapters.py, styles.py, reviews.py
│   │   ├── brainstorming.py, ideas.py
│   └── templates/              # Jinja2 模板
│       ├── base.html, dashboard.html
│       ├── project/, outline/, settings/, writer/
│       ├── review/, styles/, brainstorm/, ideas/
├── docs/
│   ├── superpowers/specs/      # 设计规格文档
│   └── superpowers/plans/      # 实施计划
├── pyproject.toml
└── README.md
```

## 页面路由

| 路由 | 页面 |
|------|------|
| `/` | 仪表盘（项目列表） |
| `/projects/{id}` | 项目工作台（功能入口） |
| `/project/{id}/outline` | 大纲编辑器（树状层级） |
| `/project/{id}/settings` | 设定集（分类浏览 + 打扫） |
| `/project/{id}/settings/{sid}` | 设定条目详情 |
| `/project/{id}/writer` | 写作编辑器（分栏布局） |
| `/project/{id}/review` | 审阅面板 |
| `/styles` | 文风库（导入 + 分析） |
| `/ideas` | 灵感便签 |
| `/brainstorm` | 头脑风暴（三种模式） |

## 实现状态

所有功能已完成开发：

- **Phase 1** — FastAPI 骨架、11 张数据表、项目 CRUD、LLM 适配器
- **Phase 2** — 大纲树状管理、设定集 CRUD + 关系图、写作编辑器
- **Phase 3** — 上下文组装、头脑风暴、文风导入与 LLM 分析
- **Phase 4** — 自动审阅引擎、设定三层打扫
- **Phase 5** — 灵感便签、差异审阅、文风混合、Token 用量追踪

## License

MIT
