---
title: Next.js + FastAPI 重构设计文档
date: 2026-06-12
status: draft
---

# Next.js + FastAPI 重构 — 架构与迁移设计

## 背景

当前项目为 FastAPI + Jinja2/HTMX/Alpine.js 全栈 SSR 应用。前端交互不够流畅、状态管理混乱、前后端耦合紧、类型安全缺失。决定将前端迁移到 Next.js (React + TypeScript)，后端保留 FastAPI 并转为纯 API 服务。

## 目标架构

```
Browser ──► Next.js (App Router) ──REST API──► FastAPI ──► SQLite
                    │                                │
                    │ openapi-typescript              │ OpenAPI spec
                    ▼                                ▼
              TypeScript types               Auto-generated docs
```

## 技术选型

| 层 | 选型 | 说明 |
|---|---|---|
| 前端框架 | Next.js 14+ (App Router) | 文件路由、React Server Components 可选 |
| 前端语言 | TypeScript | 全栈类型安全 |
| UI 组件 | shadcn/ui | 基于 Radix，可定制，轻量 |
| 样式 | Tailwind CSS (PostCSS 构建) | 已有经验，改为构建模式 |
| 全局状态 | Zustand | 零模板代码，solo 友好 |
| 服务端状态 | TanStack Query | 缓存、重试、乐观更新、SSE 流式 |
| HTTP 客户端 | fetch / ky | 轻量封装 |
| 类型生成 | openapi-typescript | FastAPI OpenAPI → .d.ts |
| 后端框架 | FastAPI (不变) | 转为纯 JSON API |
| 后端 ORM | SQLAlchemy (不变) | 结构不变 |
| 数据库 | SQLite (不变) | 未来可迁移 |

## 认证与会话管理

### 现状

当前项目**无认证机制**——所有页面和 API 端点完全公开，没有登录环节。由于是本地工具（默认绑定 127.0.0.1），这在当前部署模式下是可接受的。

### 策略：渐进式认证

迁移到前后端分离后，认证方案需要与部署方式匹配。采用渐进式策略：

| 阶段 | 认证方案 | 适用场景 |
|---|---|---|
| 开发/纯本地 | 无认证（即现状） | `localhost:3000` → `localhost:8000` |
| 内网暴露（Tailscale/Caddy） | API Key Header (`X-API-Key`) | 简单防火墙式保护 |
| 公网/生产 | JWT (httpOnly Cookie) | 全功能认证 |

由于项目当前是单用户工具，**迁移初期保持无认证状态**，但需要在后端和前端预留认证扩展点。

### API Key 方案（推荐的内网阶段）

```
Client (Next.js)                 FastAPI
       │                            │
       │  GET /api/projects         │
       │  X-API-Key: <key>         │
       │───────────────────────────►│
       │                            ├── verify_api_key()
       │                            │      ↓
       │                            │  key from .env or DB
       │      200 | 401             │
       │◄───────────────────────────│
```

配置方式：
- `.env` 中添加 `API_KEY=`（留空 = 无认证）
- FastAPI 添加全局或按需的 `Depends(verify_api_key())`
- Next.js API client 自动附加 `X-API-Key` header

### JWT 方案（未来公网阶段）

如果将来需要多用户或公网访问：

- 登录端点 `POST /api/auth/login` → 返回 JWT（存 httpOnly Cookie）
- 后端通过 `Access-Token` Cookie 或 `Authorization` header 校验
- Next.js SSR 场景：Route Handler 转发请求时携带 Cookie
- CORS 配置 `allow_credentials=True` + `allow_origins=[...]`

### 迁移中的处理

Phase 1 不引入认证，但：
- 后端添加 `app/middleware/auth.py`（空实现 + 注释说明扩展点）
- 后端添加 CORS 配置（`app/main.py`），允许 Next.js 开发服务器的跨域请求
- Phase 2 中 API client 封装预留 `authProvider` 接口

## 部署架构

### 选型：统一域名 + 反向代理

推荐方案：Nginx/Caddy 反向代理统一端口，按路径分发。

```
                        ┌─────────────────┐
                        │   Nginx / Caddy  │  :80 / :443
                        └────────┬────────┘
                                 │
                    ┌────────────┴────────────┐
                    ▼                         ▼
            ┌──────────────┐        ┌────────────────┐
            │  Next.js     │        │  FastAPI        │
            │  :3000       │        │  :8000          │
            │  /*          │        │  /api/*         │
            │             │        │                │
            │  next start  │        │  uvicorn       │
            └──────────────┘        └────────────────┘
                                            │
                                            ▼
                                       ┌────────┐
                                       │ SQLite │
                                       └────────┘
```

路径规划：
- `/*` → Next.js（所有前端页面）
- `/api/*` → FastAPI（所有后端 API）
- `/static/*` → FastAPI（用户上传文件，详见静态资源节）

### 部署模式：next start（Node.js 服务器）

理由：
- 需要 SSR（大纲/章节内容对 SEO 有一定需求）
- 需要 Next.js API Route Handler 做请求代理（SSR 场景携带 Cookie）
- `output: 'export'` 会失去 RSC、ISR、中间件等核心能力

### 开发环境

两者同时启动，通过 Next.js `rewrites` 代理 API 请求来避免 CORS 问题：

```ts
// next.config.ts
const nextConfig = {
  async rewrites() {
    return [
      { source: '/api/:path*', destination: 'http://localhost:8000/api/:path*' },
    ]
  },
}
```

启动命令通过根目录 `Makefile` 或 `npm run dev` + `uvicorn` 并行执行。

示例开发启动脚本（`scripts/dev.sh`）：

```bash
#!/bin/bash
# 启动后端
uvicorn app.main:app --reload --port 8000 &
# 启动前端
cd novel-frontend && npm run dev &
wait
```

### 生产部署（Docker Compose）

```yaml
# docker-compose.yml
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    env_file: .env

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000
    depends_on:
      - backend

  reverse-proxy:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - frontend
      - backend
```

## 后端变更

- 所有 router 返回 JSON 响应（现有 Pydantic schema 基本可用）
- 不再返回 Jinja2 HTML 模板
- 添加 CORS 中间件（`app/main.py`）
- 添加认证中间件基础结构（`app/middleware/auth.py`，初始为空实现）
- `/openapi.json` 入口供 openapi-typescript 消费
- 流式 endpoint 保持 SSE 协议不变
- 静态文件服务（历史上传文件）保持在 FastAPI 端

### 静态资源迁移

| 资源类型 | 迁移方式 |
|---|---|
| CSS/JS（`app/static/`） | 迁移到 Next.js `public/` 目录 |
| 用户上传文件（`data/` 下） | 保持由 FastAPI `/static/` 托管，Next.js 直接请求 |
| Tailwind CDN | 改为 PostCSS 构建模式 |

### CORS 配置（Phase 1 添加）

```python
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 前端项目结构

```
novel-frontend/
├── app/                          # Next.js App Router
│   ├── layout.tsx                # 根布局（含 QueryClientProvider）
│   ├── page.tsx                  # Dashboard
│   ├── login/                    # 未来：登录页
│   ├── projects/
│   │   ├── page.tsx              # 项目列表
│   │   └── [id]/
│   │       ├── page.tsx          # 项目详情
│   │       ├── outline/
│   │       ├── chapters/
│   │       ├── settings/
│   │       ├── brainstorm/       # → agent chat
│   │       ├── styles/
│   │       └── reviews/
│   └── config/
├── components/                   # 共享 UI 组件
│   ├── ui/                       # shadcn/ui 生成的组件
│   └── features/                 # 业务组件
├── lib/
│   ├── api-client.ts             # HTTP 客户端封装
│   ├── queries/                  # TanStack Query hooks
│   └── utils.ts
├── stores/                       # Zustand stores
│   └── agent.ts                  # agent 对话状态
├── types/                        # openapi-typescript 自动生成
│   └── api.d.ts
├── hooks/                        # 自定义 hooks
│   └── use-sse.ts                # SSE 连接 hook
└── public/
    └── favicon.ico
```

## 状态管理边界

| 状态类型 | 方案 | 示例 |
|---|---|---|
| 服务端数据（列表/详情） | TanStack Query | 项目列表、设定、章节 |
| 全局 UI 状态 | Zustand | 侧栏折叠、主题（未来） |
| Agent 对话状态 | Zustand | 消息列表、流式追加、loading |
| 表单状态 | React useState / 受控组件 | 创建/编辑表单 |
| 路由状态 | Next.js useParams / useSearchParams | URL 参数 |

## Agent 对话流式对接

当前 agent 使用 SSE（Server-Sent Events）。

### 关键约束

- SSE `EventSource` API 在 React Server Component 中**不可用**，必须标记 `'use client'`
- Agent 对话页面整体作为客户端组件（Client Component）
- 服务端组件中不能维持长连接

### 实现方案

```typescript
// hooks/use-sse.ts — SSE 连接管理与生命周期的 Zustand hook

// store: 消息列表 + 连接状态
interface AgentStore {
  messages: Message[]
  isConnected: boolean
  appendMessage: (msg: Message) => void
  setConnected: (v: boolean) => void
  reset: () => void
}

// hook: 管理 SSE EventSource 的创建和 cleanup
function useAgentSSE(taskId: string) {
  useEffect(() => {
    const es = new EventSource(`/api/agent/stream/${taskId}`)
    es.onmessage = (e) => appendMessage(parse(e.data))
    es.onopen = () => setConnected(true)
    es.onerror = () => setConnected(false)
    return () => es.close()  // 组件卸载时关闭连接
  }, [taskId])
}
```

### SSE 与 Next.js 兼容性

- Agent 页面标记为 `'use client'`（需要浏览器 API）
- 不为 Agent 页面使用 SSR——该页面不需要 SEO
- SSE 连接通过 Next.js `rewrites` 代理到 FastAPI，避免跨域问题

## 类型生成工作流

`openapi-typescript` 从运行中的 FastAPI 实例获取 spec：

```json
// package.json 脚本
{
  "gen:types": "openapi-typescript http://localhost:8000/openapi.json -o ./types/api.d.ts"
}
```

开发流程：
1. 后端启动（`uvicorn`） → `/openapi.json` 可用
2. 运行 `npm run gen:types` → 生成 TypeScript 类型
3. 前端类型错误 → 提示后端 API 变更了

自动化目标（Phase 4 加入）：
- `npm run dev` 并行启动后端 + 类型监听
- CI 中类型生成作为检查步骤

## 错误处理

- API client 统一拦截 HTTP 4xx/5xx，抛出结构化错误
- TanStack Query `onError` 全局 handler
- 页面级 Error Boundary（Next.js `error.tsx`）
- 全局 404/500 页面

## 性能与渲染策略

| 页面类型 | 渲染模式 | 理由 |
|---|---|---|
| Dashboard | SSG + Client fetch | 个性化数据，无需 SEO |
| 项目详情 | SSR | 需要快速首屏 |
| 设定集详情 | SSR | 内容页，适合 SEO |
| 大纲/章节 | 部分 SSR + Client hydration | 树结构复杂，混合渲染 |
| Agent 对话 | CSR ('use client') | SSE 流式，纯客户端 |
| 文风/点评 | SSG + Client fetch | 读多写少，可缓存 |
| 配置页 | CSR | 用户私有 |

### CSR 对 SEO 的影响

与当前 Jinja2 SSR 相比，部分页面改为 CSR 后搜索引擎不可见。但对于**个人写作工具**来说 SEO 不是核心需求——内容和搜索引擎收录不是本工具的目标。迁移期内不需要为此投入额外优化。

## 测试策略

### 后端测试（重构中保持）

现有 pytest 测试以 JSON API 为主，Jinja2 相关测试较少。迁移中：

- 为每个 router 补充 JSON API 测试（原有基于模板渲染的测试需要适配）
- FastAPI `TestClient` 请求方式不变（仅验证返回 JSON 而非 HTML）
- 关键路径：认证 → CRUD → SSE 流式

### 前端测试（Phase 2+ 逐步引入）

- **组件测试**: Vitest + React Testing Library，覆盖核心组件
- **集成测试**: MSW (Mock Service Worker) 拦截 API 请求
- **E2E 测试**: Playwright（仅在 Phase 4 引入，验证关键路径）

### Phase 3 中的测试步骤

每个页面迁移单独包含：
- 后端 API 测试就绪（迁移前已有或补充）
- 前端组件测试（渲染 + 交互）
- 手动验证：旧页面 → 新页面行为一致

## 迁移阶段

### Phase 1 — API 化后端（在现有仓库中完成）

目标：让 FastAPI 同时支持 JSON API 和现有模板（共存期）。

- 为每个 router 增加 `response_model` 声明，确保 Pydantic schema 完整
- 添加统一的 JSON 响应基类
- 添加 CORS 中间件（允许 `localhost:3000`）
- 添加认证中间件空架子（`app/middleware/auth.py`）
- 确保 OpenAPI spec 正确生成
- 添加 `openapi-typescript` 配置文件
- 所有 SSE endpoint 保持协议不变
- 补充每个 router 的 JSON API 测试

### Phase 2 — Next.js 项目搭建

- `create-next-app` 初始化项目（TypeScript strict mode）
- 配置 Tailwind CSS PostCSS 构建（从 CDN 迁移）
- 安装 shadcn/ui + 初始化基础组件（Button, Input, Dialog, etc.）
- 安装 Zustand + TanStack Query + openapi-typescript
- 配置 Next.js `rewrites` 代理 API 到 FastAPI
- 实现 API client + `authProvider` 接口
- 搭建根布局（Sidebar + TopNav + QueryClientProvider）
- 实现类型生成脚本 + `gen:types` npm script

### Phase 3 — 页面迁移（逐页迁移）

每个页面按 测试就绪 → 实现 → 验证 → 清理模板 的步骤执行。

优先级从低到高：

1. **Dashboard / 项目列表** — 简单列表页，验证 API 连通性
2. **设定集管理** — CRUD 表单，验证 TanStack Query mutation
3. **大纲 / 章节编辑** — 树状结构 + 富编辑，较复杂交互
4. **文风 / 点评** — 中等复杂度
5. **Agent 对话** — 流式 SSE + 复杂状态，最后迁移确保其他功能已稳定

每个页面完成后，对应的 Jinja2 模板打标记（不立即删除，以备回滚）。

### Phase 4 — 打磨

- 配置 SSR / SSG / ISR（按页需求，参见渲染策略表）
- 添加 Error Boundary、loading state、404/500 页面
- 配置类型生成自动化（dev 脚本）
- 引入前端测试（Vitest + RTL + MSW）
- 添加 Playwright E2E 测试（关键路径）
- 确认所有页面迁移完成后：
  - 删除 Jinja2 模板（`app/templates/`）
  - 删除 `app/static/`（CSS/JS，非上传文件部分）
  - 删除后端 router 中的模板渲染代码
  - 删除不再使用的 Jinja2 依赖（如果不再需要）

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|---|---|---|
| SSE 流式 + Next.js 兼容问题 | 高 | Agent 页面纯 CSR，不走 SSR，避免 RSC 限制 |
| 认证方案未定导致后期返工 | 中 | 初期无认证，但后端和客户端预留扩展点 |
| 前后端分离增加部署复杂度 | 中 | Phase 1 先用 Next.js rewrites 统一端口，简化开发 |
| 类型生成依赖后端运行 | 低 | 本地开发常驻后端，CI 中可 mock openapi.json |
| 旧模板删除后无法回滚 | 低 | Phase 3 只标记不删除，回滚由 git 管理 |
