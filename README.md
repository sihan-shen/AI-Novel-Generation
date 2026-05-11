# AI Novel Generation Tool

基于 LLM 的小说创作辅助工具。围绕创作流程设计，提供大纲管理、设定集维护、头脑风暴、文风参考、自动审阅五大核心功能。

## 功能概览

```
项目工作台 ─┬─ 大纲/细纲管理 ── 四层树状结构（卷→章→节→场景）
            │                  ├─ 多视图（树状/时间线/POV/进度）
            │                  ├─ 关联设定集
            │                  └─ LLM 节奏分析与伏笔检测
            │
            ├─ 设定集管理 ──── 结构化条目（人物/世界观/组织...）
            │                  ├─ 关系图谱（设定间逻辑关联）
            │                  ├─ LLM 可读格式（自动摘要+唯一key）
            │                  └─ 三层打扫机制（孤立检测/矛盾扫描/深度清理）
            │
            ├─ 头脑风暴 ────── 自由发散 / 上下文风暴 / 定向激荡
            │                  ├─ 发散→收敛→沉淀 工作流
            │                  └─ 灵感便签系统
            │
            ├─ 参考文风 ────── 文风库管理（LLM 自动分析）
            │                  ├─ 智能切片导入（长文本→切片→审批）
            │                  ├─ 三级应用（指令/示例/持续跟踪）
            │                  └─ 文风混合与检测
            │
            └─ 自动审阅 ────── 五维审阅（设定/文风/逻辑/语言/综合）
                               ├─ 三种模式（即时/批量/差异）
                               └─ 批量修复 / 逐项修复 / 智能修复
```

## 技术栈

| 层 | 技术 |
|----|------|
| 后端框架 | **FastAPI** (Python 3.11+) |
| 前端模板 | **Jinja2** + **HTMX** |
| 样式 | Tailwind CSS |
| 数据库 | **SQLite** (通过 SQLAlchemy ORM) |
| LLM API | Claude API / OpenAI API（可切换） |

## 快速开始

```bash
# 克隆仓库
git clone <repo-url>
cd ai-novel-generation

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置 API Key
cp .env.example .env
# 编辑 .env，填入你的 LLM API Key

# 初始化数据库
python -m app.database

# 启动服务
uvicorn app.main:app --reload --port 8000

# 打开浏览器访问 http://localhost:8000
```

## 项目结构

```
ai-novel-generation/
├── app/
│   ├── main.py                 # FastAPI 入口
│   ├── config.py               # 配置管理
│   ├── database.py             # 数据库连接
│   ├── models/                 # SQLAlchemy ORM 模型
│   ├── schemas/                # Pydantic 校验
│   ├── services/               # 业务逻辑层
│   │   ├── project_service.py
│   │   ├── outline_service.py
│   │   ├── setting_service.py
│   │   ├── chapter_service.py
│   │   ├── style_service.py
│   │   ├── review_service.py
│   │   └── brainstorm_service.py
│   ├── llm/                    # LLM 集成层
│   │   ├── adapter.py          # 抽象适配器
│   │   ├── claude_adapter.py
│   │   ├── openai_adapter.py
│   │   ├── context_builder.py  # 上下文组装
│   │   ├── templates/          # Prompt 模板
│   │   └── post_processor.py
│   ├── routers/                # API 路由
│   └── templates/              # Jinja2 页面模板
├── docs/
│   └── superpowers/specs/      # 设计规格文档
├── requirements.txt
└── README.md
```

## 页面路由

| 路由 | 页面 |
|------|------|
| `/` | 仪表盘（项目列表） |
| `/project/{id}` | 项目工作台 |
| `/project/{id}/outline` | 大纲编辑器 |
| `/project/{id}/settings` | 设定集 |
| `/project/{id}/writer` | 写作编辑器 |
| `/project/{id}/review` | 审阅面板 |
| `/styles` | 文风库 |
| `/brainstorm` | 头脑风暴 |

## 开发路线图

- **Phase 1** — FastAPI 骨架、数据模型、项目管理 CRUD
- **Phase 2** — 大纲管理器、设定集管理器、写作编辑器
- **Phase 3** — 上下文组装、头脑风暴、文风导入与应用
- **Phase 4** — 自动审阅引擎、设定集打扫
- **Phase 5** — 差异审阅、文风混合、灵感便签、打磨优化

## License

MIT
