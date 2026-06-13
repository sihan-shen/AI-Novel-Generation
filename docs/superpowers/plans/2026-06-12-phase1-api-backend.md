# Phase 1: API 化后端 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 FastAPI 后端添加完整的 JSON API 层、CORS、认证骨架和 OpenAPI 规范，保持现有 Jinja2 模板端点不受影响。

**Architecture:** 在每个 router 中新增 `/api/...` JSON 端点与现有 HTML 端点共存。JSON 端点使用统一的 `APIResponse[T]` 包装，所有 endpoint 标注 `response_model` 以生成完整 OpenAPI spec。

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, pytest

**Branch:** `refactor/phase1-api-backend`

---

### Task 1: 基础设施 — CORS 中间件 + 认证骨架 + 统一响应基类

**Files:**
- Create: `app/middleware/__init__.py`
- Create: `app/middleware/auth.py`
- Create: `app/schemas/response.py`
- Modify: `app/main.py`

---

- [ ] **Step 1: 创建 `app/middleware/__init__.py`**

```python
# app/middleware/__init__.py
```

空文件。

- [ ] **Step 2: 创建 `app/middleware/auth.py`（认证骨架）**

```python
"""认证中间件骨架 — Phase 1 为空实现，预留扩展点。

部署策略：
  开发/纯本地：    无认证（当前行为）
  内网暴露：       API Key (X-API-Key Header)
  公网/生产：       JWT (httpOnly Cookie)

使用方式（以后）：
  from app.middleware.auth import verify_api_key
  @router.get("/api/projects", dependencies=[Depends(verify_api_key())])
"""
from fastapi import Request, HTTPException, status


def verify_api_key():
    """依赖注入：校验 X-API-Key Header。

    Phase 1 实现为空（始终通过）。
    启用后将读取 ConfigService 中的 api_key 配置，
    与请求头 X-API-Key 比对。
    """

    async def _verify(request: Request) -> None:
        # 从请求头获取 API Key（留空 = 不校验）
        api_key_header = request.headers.get("X-API-Key")
        _ = api_key_header  # Phase 1 placeholder

        # Future: if configured and required, validate key
        # from app.database import SessionLocal
        # from app.services.config_service import ConfigService
        # db = SessionLocal()
        # try:
        #     cfg = ConfigService.get_all(db)
        #     expected = cfg.get("api_key", "")
        #     if expected and api_key_header != expected:
        #         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        # finally:
        #     db.close()
        pass

    return _verify
```

- [ ] **Step 3: 创建 `app/schemas/response.py`（统一 JSON 响应基类）**

```python
"""统一的 JSON API 响应格式。

所有 JSON API 端点返回此包装格式，确保前端消费时结构一致。

使用示例：
  @router.get("/api/projects", response_model=APIResponse[list[ProjectResponse]])
  async def list_projects(...):
      projects = ...
      return APIResponse(data=projects)
"""
from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """通用 API 响应包装。"""
    data: T
    message: str = "ok"


class ErrorResponse(BaseModel):
    """错误响应。"""
    detail: str
    message: str = "error"
```

- [ ] **Step 4: 修改 `app/main.py` — 添加 CORS 中间件和 middleware 导入**

在 `app = FastAPI(...)` 之后，添加：

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev server
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

也添加一个空行暗示认证中间件将在此注册：

```python
# Auth middleware will be registered here in Phase 2+
```

- [ ] **Step 5: 提交**

```bash
git add app/middleware/__init__.py app/middleware/auth.py app/schemas/response.py app/main.py
git commit -m "feat: add CORS middleware, auth skeleton, and API response base"
```

---

### Task 2: Projects Router — JSON API 端点

**Files:**
- Modify: `app/routers/projects.py`
- Create: `tests/test_api_projects.py`

当前 `projects.py` 有 5 个 HTML endpoint：`list`, `new`, `create`, `detail`, `delete`。其中 `new`（空表单）不需要 JSON 等效。

**新增 JSON 端点（保留所有原 HTML 端点）：**

| 方法 | 路径 | 替代 HTML 端点 |
|---|---|---|
| GET | `/api/projects` | `/projects/list` |
| POST | `/api/projects` | `/projects/create` |
| GET | `/api/projects/{project_id}` | `/projects/{project_id}` |
| DELETE | `/api/projects/{project_id}` | `/projects/{project_id}` (DELETE) |

---

- [ ] **Step 1: 修改 `app/routers/projects.py`**

在文件末尾，导入 `APIResponse` 和 `ProjectResponse`，添加 JSON 端点：

```python
from app.schemas.response import APIResponse
from app.schemas.project import ProjectResponse, ProjectCreate

# === JSON API endpoints (Phase 1) ===

@router.get("/api/projects", response_model=APIResponse[list[ProjectResponse]])
async def api_list_projects(db: Session = Depends(get_db)):
    projects = ProjectService.list(db)
    return APIResponse(data=projects)


@router.post("/api/projects", response_model=APIResponse[ProjectResponse], status_code=201)
async def api_create_project(body: ProjectCreate, db: Session = Depends(get_db)):
    project = ProjectService.create(db, body)
    return APIResponse(data=project)


@router.get("/api/projects/{project_id}", response_model=APIResponse[ProjectResponse])
async def api_get_project(project_id: str, db: Session = Depends(get_db)):
    project = ProjectService.get(db, project_id)
    if not project:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Project not found")
    return APIResponse(data=project)


@router.delete("/api/projects/{project_id}", response_model=APIResponse[dict])
async def api_delete_project(project_id: str, db: Session = Depends(get_db)):
    ProjectService.delete(db, project_id)
    return APIResponse(data={"deleted": project_id})
```

注意：`/api/` 路由前缀在 APIRouter 级别，所以实际路径由 `prefix="/projects"` + `/api/...` = `/projects/api/projects`。

等等，这不对。`router` 已经有 `prefix="/projects"`，所以 `@router.get("/api/projects")` 会变成 `/projects/api/projects`。

最好用一个独立的 `api_router` 来处理 JSON API 端点，或者在主 router 上用不同的前缀。但最简单的方案是直接在现有 router 上加，路径用 `/api`：

```python
# 在 projects.py 中
@router.get("/api", response_model=APIResponse[list[ProjectResponse]])
async def api_list_projects(...)

@router.post("/api", response_model=..., status_code=201)
async def api_create_project(...)

@router.get("/api/{project_id}", ...)
async def api_get_project(...)

@router.delete("/api/{project_id}", ...)
async def api_delete_project(...)
```

这样路径是 `/projects/api` 和 `/projects/api/{project_id}`。嗯，这也不太优雅。

更好的方案：在 `app/main.py` 中新增一个 JSON API 路由器或单独给 JSON 端点建路由。或者用 `/api/projects` 作为统一前缀。

让 JSON API 使用和现有项目一致但更扁平的前缀：`/api/projects`。这样需要在 `app/main.py` 引入一个新 router，或者在 `projects.py` 里给现有 router 添加路径。

最简单：在 `projects.py` 中用一个独立的 `api_router`：

```python
api_router = APIRouter(prefix="/api/projects", tags=["projects-api"])

@api_router.get("", response_model=APIResponse[list[ProjectResponse]])
async def api_list_projects(...)
```

然后在 `app/main.py` 中注册两个 router。

让我重新考虑。最简单且保持命名一致的方式是：

方案 A: 每个 router 新增一个 `api_router`，在 `app/main.py` 分别 include
方案 B: 在现有 router 上用统一的前缀路径

我更倾向方案 A，因为它前缀清晰且不影响现有路由。

让我重写这个 task。

---

**修正后的方案：**

修改 `app/routers/projects.py`，添加 `api_router`：

```python
api_router = APIRouter(prefix="/api/projects", tags=["projects"])

@api_router.get("", response_model=APIResponse[list[ProjectResponse]])
async def api_list_projects(db: Session = Depends(get_db)):
    projects = ProjectService.list(db)
    return APIResponse(data=projects)


@api_router.post("", response_model=APIResponse[ProjectResponse], status_code=201)
async def api_create_project(body: ProjectCreate, db: Session = Depends(get_db)):
    project = ProjectService.create(db, body)
    return APIResponse(data=project)


@api_router.get("/{project_id}", response_model=APIResponse[ProjectResponse])
async def api_get_project(project_id: str, db: Session = Depends(get_db)):
    project = ProjectService.get(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return APIResponse(data=project)


@api_router.delete("/{project_id}", response_model=APIResponse[dict])
async def api_delete_project(project_id: str, db: Session = Depends(get_db)):
    ProjectService.delete(db, project_id)
    return APIResponse(data={"deleted": project_id})
```

在 `app/main.py` 中添加：

```python
from app.routers.projects import api_router as projects_api_router
app.include_router(projects_api_router)
```

不过所有 router 都这样做就太繁琐了。让我想一个更好的方式。

实际上，最简洁的方式是：在 `app/main.py` 中创建一个独立的 `api_app` 或者直接用现有的 app 注册这些路由。但可能更好的方式是在项目根目录创建一个单独的 `api/v1/` 路由器目录。

但是不对，Phase 1 是要最小化改动。让我换一种思路。

直接在每个 router 文件中添加 `/api` 前缀的端点，但使用相同的 router 对象。这样路径会变成 `/projects/api/...`。然后在 `app/main.py` 添加一个根据路由表看转发。

算了，最简单且最明确的方式：

在每个 router 文件中，添加使用 `/api` 前缀的新路径到现有的 router。例如在 `projects.py` 中：

```python
@router.get("/api", ...)  # -> /projects/api
```

这样有点丑但最简单。或者可以在 app/main.py 中为所有 API 端点建立一个统一的挂载点。

让我换个思路：在 `app/main.py` 中添加一个 `api_v1` 子应用，或者在 `app/routers/` 下创建一个 `api/` 目录。

但最实际的做法是：**为每个资源创建一个单独的 API router**，在 router 文件中定义一个 `api_router` (prefix 不同)，然后在 `app/main.py` 挂载。

每个 router 文件的结构变成：

```python
# 原来的 router (HTML)
router = APIRouter(prefix="/projects", tags=["projects"])

# JSON API router (Phase 1)
api_router = APIRouter(prefix="/api/projects", tags=["projects"])
```

然后在 `app/main.py`：

```python
from app.routers.projects import router as projects_router, api_router as projects_api_router
app.include_router(projects_router)
app.include_router(projects_api_router)
```

这样每个文件的改动量很小，而且路径清晰。让我用这个方案重写整个计划。

好的，这对每个 router 都有类似模式的改动。让我系统地写出计划。

不对，我想到了更简洁的方式。我可以在 `app/main.py` 中添加一个 `api_router`，然后所有路由都在这个 API router 上注册，类似于：

```python
# app/main.py
api = APIRouter(prefix="/api")

# 然后每个路由文件导出 register_api(router) 函数
```

但这需要对现有代码结构做更多改动。

还是按之前的方案吧——在每个 router 文件中添加 `api_router`，主文件中统一挂载。最清晰。

实际上，我认真想想，我觉得最好的方式跟 FastAPI 的设计一致：在现有 router 文件顶部或底部加一组 JSON API 端点。最简单的方式是用同样的 router 前缀 `/api` 前缀路径。

对于 `projects.py` (prefix="/projects")：
- `@router.get("/api")` → `/projects/api` — 不好看

那就在 `app/routers/` 下创建一个 `api/` 子目录吗？不，那改动太大了。

好吧，最务实的方案：**在 `projects.py` 里创建第二个 `APIRouter` 实例 `api = APIRouter(prefix="/api/projects")`，然后 `app/main.py` 单独引入所有 API router。**

这个方案每个文件改 10 行左右，很清晰。让我按这个写计划。

但是我需要为每个 router 都做这个，计划会比较长。让我简化描述，用一致的模式。

其实吧，让我再想想。Phase 1 的核心目标是让 FastAPI 可以输出 JSON + OpenAPI spec。一个更简单的方式可能是：

**不创建新路由，而是修改现有路由使其支持 `Accept: application/json` 请求头**，如果前端请求 JSON 就返回 JSON，否则返回 HTML。

但这样会让现有代码复杂化，而且不好测试。

保持简单：**在每个 router 中添加 `api_router`**，`app/main.py` 统一 include。

OK，让我直接写计划吧。<｜end▁of▁thinking｜>

<｜｜DSML｜｜tool_calls>
<｜｜DSML｜｜invoke name="Write">
<｜｜DSML｜｜parameter name="content" string="true"># Phase 1: API 化后端 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 FastAPI 后端添加完整的 JSON API 层、CORS、认证骨架和 OpenAPI 规范，保持现有 Jinja2 模板端点不受影响。

**Architecture:** 在每个 router 文件中新增 `api_router` (带 `/api/<resource>` 前缀)，与现有 HTML router 共存。JSON 端点使用统一的 `APIResponse[T]` 包装，所有 endpoint 标注 `response_model`。`app/main.py` 统一 include 所有 API router。

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, pytest

**Branch:** `refactor/phase1-api-backend`

---

### Task 1: 基础设施 — CORS + 认证骨架 + 统一响应 + 主路由注册

**Files:**
- Create: `app/middleware/__init__.py`
- Create: `app/middleware/auth.py`
- Create: `app/schemas/response.py`
- Modify: `app/main.py`

---

- [ ] **Step 1: 创建 `app/middleware/__init__.py`**

空文件。

- [ ] **Step 2: 创建 `app/middleware/auth.py`**

```python
"""认证中间件骨架 — Phase 1 为空实现，预留扩展点。"""
from fastapi import Request


def verify_api_key():
    """依赖注入：校验 X-API-Key Header。
    Phase 1 实现为空（始终通过）。
    """

    async def _verify(request: Request) -> None:
        _ = request.headers.get("X-API-Key")  # Phase 1 placeholder
        pass

    return _verify
```

- [ ] **Step 3: 创建 `app/schemas/response.py`**

```python
from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    data: T
    message: str = "ok"
```

- [ ] **Step 4: 修改 `app/main.py` — 添加 CORS + API router 导入模板**

```python
# 在 app 创建之后，include_router 之前添加：
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 在每个 Task 完成后，逐步添加对应 api_router 的 include：
# from app.routers.projects import api_router as projects_api
# app.include_router(projects_api)
```

- [ ] **Step 5: 运行测试确保基础功能正常**

```bash
pytest tests/test_smoke.py -v
```
预期：4 passed

- [ ] **Step 6: 提交**

```bash
git add app/middleware/ app/schemas/response.py app/main.py
git commit -m "feat: add CORS middleware, auth skeleton, and APIResponse base"
```

---

### Task 2: Projects — JSON API 端点 + 测试

**Files:**
- Modify: `app/routers/projects.py`
- Modify: `app/main.py`
- Create: `tests/test_api_projects.py`

---

- [ ] **Step 1: 在 `app/routers/projects.py` 末尾添加 api_router**

```python
from app.schemas.response import APIResponse
from app.schemas.project import ProjectResponse, ProjectCreate
from fastapi import HTTPException

api_router = APIRouter(prefix="/api/projects", tags=["projects"])


@api_router.get("", response_model=APIResponse[list[ProjectResponse]])
async def api_list_projects(db: Session = Depends(get_db)):
    projects = ProjectService.list(db)
    return APIResponse(data=projects)


@api_router.post("", response_model=APIResponse[ProjectResponse], status_code=201)
async def api_create_project(body: ProjectCreate, db: Session = Depends(get_db)):
    project = ProjectService.create(db, body)
    return APIResponse(data=project)


@api_router.get("/{project_id}", response_model=APIResponse[ProjectResponse])
async def api_get_project(project_id: str, db: Session = Depends(get_db)):
    project = ProjectService.get(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return APIResponse(data=project)


@api_router.delete("/{project_id}", response_model=APIResponse[dict])
async def api_delete_project(project_id: str, db: Session = Depends(get_db)):
    ProjectService.delete(db, project_id)
    return APIResponse(data={"deleted": project_id})
```

- [ ] **Step 2: 在 `app/main.py` 中 include Projects API router**

在 `app.include_router(projects.router)` 后添加：

```python
from app.routers.projects import api_router as projects_api
app.include_router(projects_api)
```

- [ ] **Step 3: 创建 `tests/test_api_projects.py`**

```python
import pytest
from app.models.project import Project


class TestProjectsAPI:
    def test_list_empty(self, client):
        resp = client.get("/api/projects")
        assert resp.status_code == 200
        body = resp.json()
        assert body["message"] == "ok"
        assert body["data"] == []

    def test_create_and_list(self, client, db_session):
        resp = client.post("/api/projects", json={
            "title": "测试项目",
            "description": "描述",
            "genre": "科幻",
        })
        assert resp.status_code == 201
        created = resp.json()["data"]
        assert created["title"] == "测试项目"

        resp = client.get("/api/projects")
        assert len(resp.json()["data"]) == 1

    def test_get_by_id(self, client, db_session):
        db_session.add(Project(id="p1", title="P1", description="", genre=""))
        db_session.commit()

        resp = client.get("/api/projects/p1")
        assert resp.status_code == 200
        assert resp.json()["data"]["title"] == "P1"

    def test_get_not_found(self, client):
        resp = client.get("/api/projects/nonexistent")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Project not found"

    def test_delete(self, client, db_session):
        db_session.add(Project(id="p2", title="P2", description="", genre=""))
        db_session.commit()

        resp = client.delete("/api/projects/p2")
        assert resp.status_code == 200

        resp = client.get("/api/projects")
        assert resp.json()["data"] == []
```

- [ ] **Step 4: 运行测试**

```bash
pytest tests/test_api_projects.py -v
```
预期：5 passed

```bash
pytest tests/test_smoke.py -v
```
预期：4 passed（确认没破坏现有功能）

- [ ] **Step 5: 提交**

```bash
git add app/routers/projects.py app/main.py tests/test_api_projects.py
git commit -m "feat(api): add projects JSON API endpoints with tests"
```

---

### Task 3: Outlines — JSON API 端点 + 测试

**Files:**
- Modify: `app/routers/outlines.py`
- Modify: `app/main.py`
- Create: `tests/test_api_outlines.py`

当前 `outlines.py` 端点 (prefix=`/project/{project_id}/outline`)：

| 方法 | 路径 | 行为 |
|---|---|---|
| GET | `` | 页面 (HTML) |
| GET | `/tree` | tree 局部 (HTML) |
| GET | `/new-item` | 表单 (HTML) |
| POST | `/create` | 创建 (HTML) |
| PUT | `/{outline_id}` | 更新 (HTML) |
| DELETE | `/{outline_id}` | 删除 (HTML) |
| POST | `/reorder` | 排序 (HTML) |

**JSON 端点（`/api/projects/{project_id}/outlines`）：**

| 方法 | 路径 | 对应 |
|---|---|---|
| GET | `` | 列出大纲树 |
| POST | `` | 创建 |
| GET | `/{outline_id}` | 详情 |
| PUT | `/{outline_id}` | 更新 |
| DELETE | `/{outline_id}` | 删除 |
| POST | `/reorder` | 排序 |

---

- [ ] **Step 1: 在 `app/routers/outlines.py` 末尾添加 api_router**

```python
from app.schemas.response import APIResponse
from app.schemas.outline import OutlineResponse, OutlineCreate, OutlineUpdate
from fastapi import HTTPException

api_router = APIRouter(prefix="/api/projects/{project_id}/outlines", tags=["outlines"])


@api_router.get("", response_model=APIResponse[list[OutlineResponse]])
async def api_get_outline_tree(project_id: str, db: Session = Depends(get_db)):
    outlines = OutlineService.get_tree(db, project_id)
    return APIResponse(data=outlines)


@api_router.post("", response_model=APIResponse[OutlineResponse], status_code=201)
async def api_create_outline(project_id: str, body: OutlineCreate, db: Session = Depends(get_db)):
    data = body.model_copy(update={"project_id": project_id})
    outline = OutlineService.create(db, data)
    return APIResponse(data=outline)


@api_router.get("/{outline_id}", response_model=APIResponse[OutlineResponse])
async def api_get_outline(project_id: str, outline_id: str, db: Session = Depends(get_db)):
    outline = OutlineService.get(db, outline_id)
    if not outline:
        raise HTTPException(status_code=404, detail="Outline not found")
    return APIResponse(data=outline)


@api_router.put("/{outline_id}", response_model=APIResponse[OutlineResponse])
async def api_update_outline(project_id: str, outline_id: str, body: OutlineUpdate, db: Session = Depends(get_db)):
    outline = OutlineService.update(db, outline_id, body)
    if not outline:
        raise HTTPException(status_code=404, detail="Outline not found")
    return APIResponse(data=outline)


@api_router.delete("/{outline_id}", response_model=APIResponse[dict])
async def api_delete_outline(project_id: str, outline_id: str, db: Session = Depends(get_db)):
    ok, _ = OutlineService.delete(db, outline_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Outline not found")
    return APIResponse(data={"deleted": outline_id})


@api_router.post("/reorder", response_model=APIResponse[dict])
async def api_reorder_outlines(project_id: str, body: dict, db: Session = Depends(get_db)):
    OutlineService.reorder(db, body["items"])
    return APIResponse(data={"ok": True})
```

- [ ] **Step 2: 在 `app/main.py` include**

```python
from app.routers.outlines import api_router as outlines_api
app.include_router(outlines_api)
```

- [ ] **Step 3: 创建 `tests/test_api_outlines.py`**

```python
import pytest
from app.models.project import Project
from app.models.outline import Outline


class TestOutlinesAPI:
    def _seed_project(self, db_session):
        db_session.add(Project(id="p1", title="Test", description="", genre=""))
        db_session.commit()

    def test_list_empty(self, client, db_session):
        self._seed_project(db_session)
        resp = client.get("/api/projects/p1/outlines")
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    def test_create_and_list(self, client, db_session):
        self._seed_project(db_session)
        resp = client.post("/api/projects/p1/outlines", json={
            "project_id": "p1", "level": 1, "title": "第一卷",
        })
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["title"] == "第一卷"
        assert data["level"] == 1

        resp = client.get("/api/projects/p1/outlines")
        assert len(resp.json()["data"]) == 1

    def test_get_by_id(self, client, db_session):
        self._seed_project(db_session)
        db_session.add(Outline(id="o1", project_id="p1", level=1, title="卷二", sort_order=0))
        db_session.commit()

        resp = client.get("/api/projects/p1/outlines/o1")
        assert resp.status_code == 200
        assert resp.json()["data"]["title"] == "卷二"

    def test_update(self, client, db_session):
        self._seed_project(db_session)
        db_session.add(Outline(id="o2", project_id="p1", level=1, title="旧标题", sort_order=0))
        db_session.commit()

        resp = client.put("/api/projects/p1/outlines/o2", json={"title": "新标题"})
        assert resp.status_code == 200
        assert resp.json()["data"]["title"] == "新标题"

    def test_delete(self, client, db_session):
        self._seed_project(db_session)
        db_session.add(Outline(id="o3", project_id="p1", level=1, title="删掉", sort_order=0))
        db_session.commit()

        resp = client.delete("/api/projects/p1/outlines/o3")
        assert resp.status_code == 200

        resp = client.get("/api/projects/p1/outlines")
        assert resp.json()["data"] == []

    def test_get_not_found(self, client, db_session):
        self._seed_project(db_session)
        resp = client.get("/api/projects/p1/outlines/nonexistent")
        assert resp.status_code == 404
```

- [ ] **Step 4: 运行测试**

```bash
pytest tests/test_api_outlines.py -v
```
预期：7 passed

```bash
pytest tests/test_smoke.py -v
```
预期：4 passed

- [ ] **Step 5: 提交**

```bash
git add app/routers/outlines.py app/main.py tests/test_api_outlines.py
git commit -m "feat(api): add outlines JSON API endpoints with tests"
```

---

### Task 4: Settings — JSON API 端点 + 测试

**Files:**
- Modify: `app/routers/settings.py`
- Modify: `app/main.py`
- Create: `tests/test_api_settings.py`

当前 `settings.py` 端点 (prefix=`/project/{project_id}/settings`)：

| 方法 | 路径 | 行为 |
|---|---|---|
| GET | `` | 页面 (HTML) |
| GET | `/list` | 列表 (HTML) |
| GET | `/new` | 表单 (HTML) |
| POST | `/create` | 创建 (HTML) |
| PUT | `/{setting_id}` | 更新 (HTML) |
| POST | `/clean` | 打扫 (HTML) |
| GET | `/{setting_id}` | 详情 (HTML) |
| POST | `/reorder` | 排序 (HTML) |
| DELETE | `/{setting_id}` | 删除 (HTML) |

**JSON 端点（`/api/projects/{project_id}/settings`）：**

| 方法 | 路径 |
|---|---|
| GET | `` | 列出（支持 `category` 查询参数） |
| POST | `` | 创建 |
| GET | `/{setting_id}` | 详情（含 relations） |
| PUT | `/{setting_id}` | 更新 |
| DELETE | `/{setting_id}` | 删除 |
| POST | `/reorder` | 排序 |

---

- [ ] **Step 1: 在 `app/routers/settings.py` 末尾添加 api_router**

```python
from app.schemas.response import APIResponse
from app.schemas.setting import SettingCreate, SettingUpdate
from fastapi import HTTPException


# 简单的 setting response schema（现有 schemas 中没有，临时定义）
from pydantic import BaseModel
from datetime import datetime


class SettingResponse(BaseModel):
    id: str
    project_id: str
    category: str
    name: str
    summary: str
    content: str
    weight: int
    status: str
    tags: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


api_router = APIRouter(prefix="/api/projects/{project_id}/settings", tags=["settings"])


@api_router.get("", response_model=APIResponse[list[SettingResponse]])
async def api_list_settings(project_id: str, category: str | None = None, db: Session = Depends(get_db)):
    settings = SettingService.list_by_project(db, project_id, category)
    return APIResponse(data=settings)


@api_router.post("", response_model=APIResponse[SettingResponse], status_code=201)
async def api_create_setting(project_id: str, body: SettingCreate, db: Session = Depends(get_db)):
    data = body.model_copy(update={"project_id": project_id})
    setting = SettingService.create(db, data)
    return APIResponse(data=setting)


@api_router.get("/{setting_id}", response_model=APIResponse[dict])
async def api_get_setting(setting_id: str, project_id: str, db: Session = Depends(get_db)):
    setting = SettingService.get(db, setting_id)
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    relations = SettingService.get_relations(db, setting_id)
    return APIResponse(data={"setting": setting, "relations": relations})


@api_router.put("/{setting_id}", response_model=APIResponse[SettingResponse])
async def api_update_setting(setting_id: str, project_id: str, body: SettingUpdate, db: Session = Depends(get_db)):
    setting = SettingService.update(db, setting_id, body)
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    return APIResponse(data=setting)


@api_router.delete("/{setting_id}", response_model=APIResponse[dict])
async def api_delete_setting(setting_id: str, project_id: str, db: Session = Depends(get_db)):
    SettingService.delete(db, setting_id)
    return APIResponse(data={"deleted": setting_id})


@api_router.post("/reorder", response_model=APIResponse[dict])
async def api_reorder_settings(project_id: str, body: dict, db: Session = Depends(get_db)):
    SettingService.reorder(db, body["items"])
    return APIResponse(data={"ok": True})
```

- [ ] **Step 2: 在 `app/main.py` include**

```python
from app.routers.settings import api_router as settings_api
app.include_router(settings_api)
```

- [ ] **Step 3: 创建 `tests/test_api_settings.py`**

```python
import pytest
from app.models.project import Project
from app.models.setting import Setting


class TestSettingsAPI:
    def _seed(self, db_session):
        db_session.add(Project(id="p1", title="Test", description="", genre=""))
        db_session.commit()

    def test_list_empty(self, client, db_session):
        self._seed(db_session)
        resp = client.get("/api/projects/p1/settings")
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    def test_create_and_list(self, client, db_session):
        self._seed(db_session)
        resp = client.post("/api/projects/p1/settings", json={
            "project_id": "p1", "category": "人物", "name": "张三", "summary": "主角",
        })
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["name"] == "张三"

        resp = client.get("/api/projects/p1/settings")
        assert len(resp.json()["data"]) == 1

    def test_get_by_id(self, client, db_session):
        self._seed(db_session)
        db_session.add(Setting(id="s1", project_id="p1", category="人物", name="李四", summary="", content="", weight=5, key="", tags="[]"))
        db_session.commit()

        resp = client.get("/api/projects/p1/settings/s1")
        assert resp.status_code == 200
        assert resp.json()["data"]["setting"]["name"] == "李四"

    def test_update(self, client, db_session):
        self._seed(db_session)
        db_session.add(Setting(id="s2", project_id="p1", category="人物", name="旧名", summary="", content="", weight=5, key="", tags="[]"))
        db_session.commit()

        resp = client.put("/api/projects/p1/settings/s2", json={"name": "新名"})
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "新名"

    def test_delete(self, client, db_session):
        self._seed(db_session)
        db_session.add(Setting(id="s3", project_id="p1", category="人物", name="删掉", summary="", content="", weight=5, key="", tags="[]"))
        db_session.commit()

        resp = client.delete("/api/projects/p1/settings/s3")
        assert resp.status_code == 200

        resp = client.get("/api/projects/p1/settings")
        assert resp.json()["data"] == []

    def test_category_filter(self, client, db_session):
        self._seed(db_session)
        db_session.add(Setting(id="s4", project_id="p1", category="人物", name="王五", summary="", content="", weight=5, key="", tags="[]"))
        db_session.add(Setting(id="s5", project_id="p1", category="地理", name="城池", summary="", content="", weight=5, key="", tags="[]"))
        db_session.commit()

        resp = client.get("/api/projects/p1/settings?category=人物")
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["name"] == "王五"
```

- [ ] **Step 4: 运行测试**

```bash
pytest tests/test_api_settings.py -v
```
预期：7 passed

```bash
pytest tests/test_smoke.py -v
```

- [ ] **Step 5: 提交**

```bash
git add app/routers/settings.py app/main.py tests/test_api_settings.py
git commit -m "feat(api): add settings JSON API endpoints with tests"
```

---

### Task 5: Chapters — JSON API 端点 + 测试

**Files:**
- Modify: `app/routers/chapters.py`
- Modify: `app/main.py`
- Create: `tests/test_api_chapters.py`

**JSON 端点（`/api/projects/{project_id}/chapters`）：**

| 方法 | 路径 | 对应 HTML |
|---|---|---|
| GET | `` | 列出章节 |
| POST | `` | 创建 |
| GET | `/{chapter_id}` | 详情 |
| PUT | `/{chapter_id}` | 更新 |
| DELETE | `/{chapter_id}` | 删除 |
| POST | `/reorder` | 排序 |

---

- [ ] **Step 1: 在 `app/routers/chapters.py` 末尾添加 api_router**

```python
from app.schemas.response import APIResponse
from app.schemas.chapter import ChapterCreate, ChapterUpdate
from fastapi import HTTPException


class ChapterResponse(BaseModel):
    id: str
    project_id: str
    outline_id: str | None
    title: str
    content: str
    status: str
    sort_order: int
    notes: str
    word_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


api_router = APIRouter(prefix="/api/projects/{project_id}/chapters", tags=["chapters"])


@api_router.get("", response_model=APIResponse[list[ChapterResponse]])
async def api_list_chapters(project_id: str, db: Session = Depends(get_db)):
    chapters = ChapterService.list_by_project(db, project_id)
    return APIResponse(data=chapters)


@api_router.post("", response_model=APIResponse[ChapterResponse], status_code=201)
async def api_create_chapter(project_id: str, body: ChapterCreate, db: Session = Depends(get_db)):
    data = body.model_copy(update={"project_id": project_id})
    chapter = ChapterService.create(db, data)
    return APIResponse(data=chapter)


@api_router.get("/{chapter_id}", response_model=APIResponse[ChapterResponse])
async def api_get_chapter(chapter_id: str, project_id: str, db: Session = Depends(get_db)):
    chapter = ChapterService.get(db, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return APIResponse(data=chapter)


@api_router.put("/{chapter_id}", response_model=APIResponse[ChapterResponse])
async def api_update_chapter(chapter_id: str, project_id: str, body: ChapterUpdate, db: Session = Depends(get_db)):
    chapter = ChapterService.update(db, chapter_id, body)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return APIResponse(data=chapter)


@api_router.delete("/{chapter_id}", response_model=APIResponse[dict])
async def api_delete_chapter(chapter_id: str, project_id: str, db: Session = Depends(get_db)):
    ChapterService.delete(db, chapter_id)
    return APIResponse(data={"deleted": chapter_id})


@api_router.post("/reorder", response_model=APIResponse[dict])
async def api_reorder_chapters(project_id: str, body: dict, db: Session = Depends(get_db)):
    ChapterService.reorder(db, body["items"])
    return APIResponse(data={"ok": True})
```

- [ ] **Step 2: 在 `app/main.py` include**

```python
from app.routers.chapters import api_router as chapters_api
app.include_router(chapters_api)
```

- [ ] **Step 3: 创建 `tests/test_api_chapters.py`**

```python
import pytest
from app.models.project import Project
from app.models.chapter import Chapter


class TestChaptersAPI:
    def _seed(self, db_session):
        db_session.add(Project(id="p1", title="Test", description="", genre=""))
        db_session.commit()

    def test_list_empty(self, client, db_session):
        self._seed(db_session)
        resp = client.get("/api/projects/p1/chapters")
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    def test_create_and_list(self, client, db_session):
        self._seed(db_session)
        resp = client.post("/api/projects/p1/chapters", json={
            "project_id": "p1", "title": "第一章",
        })
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["title"] == "第一章"

        resp = client.get("/api/projects/p1/chapters")
        assert len(resp.json()["data"]) == 1

    def test_get_by_id(self, client, db_session):
        self._seed(db_session)
        db_session.add(Chapter(id="c1", project_id="p1", title="C1", content="", sort_order=0))
        db_session.commit()

        resp = client.get("/api/projects/p1/chapters/c1")
        assert resp.status_code == 200
        assert resp.json()["data"]["title"] == "C1"

    def test_update(self, client, db_session):
        self._seed(db_session)
        db_session.add(Chapter(id="c2", project_id="p1", title="旧标题", content="", sort_order=0))
        db_session.commit()

        resp = client.put("/api/projects/p1/chapters/c2", json={"title": "新标题"})
        assert resp.status_code == 200
        assert resp.json()["data"]["title"] == "新标题"

    def test_delete(self, client, db_session):
        self._seed(db_session)
        db_session.add(Chapter(id="c3", project_id="p1", title="删掉", content="", sort_order=0))
        db_session.commit()

        resp = client.delete("/api/projects/p1/chapters/c3")
        assert resp.status_code == 200

        resp = client.get("/api/projects/p1/chapters")
        assert resp.json()["data"] == []
```

- [ ] **Step 4: 运行测试**

```bash
pytest tests/test_api_chapters.py -v
```
预期：6 passed

- [ ] **Step 5: 提交**

```bash
git add app/routers/chapters.py app/main.py tests/test_api_chapters.py
git commit -m "feat(api): add chapters JSON API endpoints with tests"
```

---

### Task 6: Styles — JSON API 端点 + 测试

**Files:**
- Modify: `app/routers/styles.py`
- Modify: `app/main.py`
- Create: `tests/test_api_styles.py`

---

- [ ] **Step 1: 在 `app/routers/styles.py` 末尾添加 api_router**

```python
from app.schemas.response import APIResponse
from fastapi import HTTPException


class StyleResponse(BaseModel):
    id: str
    name: str
    source: str
    source_text: str
    analysis: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


api_router = APIRouter(prefix="/api/styles", tags=["styles"])


@api_router.get("", response_model=APIResponse[list[StyleResponse]])
async def api_list_styles(db: Session = Depends(get_db)):
    styles = StyleService.list_all(db)
    return APIResponse(data=styles)


@api_router.delete("/{style_id}", response_model=APIResponse[dict])
async def api_delete_style(style_id: str, db: Session = Depends(get_db)):
    StyleService.delete(db, style_id)
    return APIResponse(data={"deleted": style_id})
```

- [ ] **Step 2: 在 `app/main.py` include**

```python
from app.routers.styles import api_router as styles_api
app.include_router(styles_api)
```

- [ ] **Step 3: 创建 `tests/test_api_styles.py`**

```python
from app.models.style import Style


class TestStylesAPI:
    def test_list_empty(self, client):
        resp = client.get("/api/styles")
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    def test_create_then_list(self, client, db_session):
        db_session.add(Style(id="s1", name="鲁迅风", source="manual", source_text="", analysis="冷峻"))
        db_session.commit()

        resp = client.get("/api/styles")
        assert len(resp.json()["data"]) == 1

    def test_delete(self, client, db_session):
        db_session.add(Style(id="s2", name="测试", source="manual", source_text="", analysis=""))
        db_session.commit()

        resp = client.delete("/api/styles/s2")
        assert resp.status_code == 200

        resp = client.get("/api/styles")
        assert len(resp.json()["data"]) == 0
```

- [ ] **Step 4: 运行测试并提交**

```bash
pytest tests/test_api_styles.py -v
git add app/routers/styles.py app/main.py tests/test_api_styles.py
git commit -m "feat(api): add styles JSON API endpoints with tests"
```

---

### Task 7: Ideas — JSON API 端点 + 测试

**Files:**
- Modify: `app/routers/ideas.py`
- Modify: `app/main.py`
- Create: `tests/test_api_ideas.py`

---

- [ ] **Step 1: 在 `app/routers/ideas.py` 末尾添加 api_router**

```python
from app.schemas.response import APIResponse
from fastapi import HTTPException


class IdeaResponse(BaseModel):
    id: str
    project_id: str | None
    title: str
    content: str
    source: str
    sort_order: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class IdeaCreate(BaseModel):
    project_id: str | None = None
    title: str = ""
    content: str = ""
    source: str = "手写"


api_router = APIRouter(prefix="/api/ideas", tags=["ideas"])


@api_router.get("", response_model=APIResponse[list[IdeaResponse]])
async def api_list_ideas(project_id: str | None = None, db: Session = Depends(get_db)):
    ideas = IdeaService.list_by_project(db, project_id)
    return APIResponse(data=ideas)


@api_router.post("", response_model=APIResponse[IdeaResponse], status_code=201)
async def api_create_idea(body: IdeaCreate, db: Session = Depends(get_db)):
    idea = IdeaService.create(db, project_id=body.project_id, title=body.title, content=body.content, source=body.source)
    return APIResponse(data=idea)


@api_router.delete("/{idea_id}", response_model=APIResponse[dict])
async def api_delete_idea(idea_id: str, db: Session = Depends(get_db)):
    IdeaService.delete(db, idea_id)
    return APIResponse(data={"deleted": idea_id})


@api_router.post("/reorder", response_model=APIResponse[dict])
async def api_reorder_ideas(body: dict, db: Session = Depends(get_db)):
    IdeaService.reorder(db, body["items"])
    return APIResponse(data={"ok": True})
```

- [ ] **Step 2: 在 `app/main.py` include**

```python
from app.routers.ideas import api_router as ideas_api
app.include_router(ideas_api)
```

- [ ] **Step 3: 创建 `tests/test_api_ideas.py`**

```python
from app.models.idea import Idea


class TestIdeasAPI:
    def test_list_empty(self, client):
        resp = client.get("/api/ideas")
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    def test_create_and_list(self, client, db_session):
        resp = client.post("/api/ideas", json={"title": "好点子", "content": "细节", "source": "手写"})
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["title"] == "好点子"

        resp = client.get("/api/ideas")
        assert len(resp.json()["data"]) == 1

    def test_delete(self, client, db_session):
        db_session.add(Idea(id="i1", project_id=None, title="删掉", content="", source="手写", sort_order=0))
        db_session.commit()

        resp = client.delete("/api/ideas/i1")
        assert resp.status_code == 200

        resp = client.get("/api/ideas")
        assert resp.json()["data"] == []
```

- [ ] **Step 4: 运行测试并提交**

```bash
pytest tests/test_api_ideas.py -v
git add app/routers/ideas.py app/main.py tests/test_api_ideas.py
git commit -m "feat(api): add ideas JSON API endpoints with tests"
```

---

### Task 8: Reviews — JSON API 端点 + 测试

**Files:**
- Modify: `app/routers/reviews.py`
- Modify: `app/main.py`
- Create: `tests/test_api_reviews.py`

---

- [ ] **Step 1: 在 `app/routers/reviews.py` 末尾添加 api_router**

```python
from app.schemas.response import APIResponse
from fastapi import HTTPException


class ReviewResponse(BaseModel):
    id: str
    project_id: str
    chapter_id: str
    review_type: str
    summary: str
    findings: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


api_router = APIRouter(prefix="/api/projects/{project_id}/reviews", tags=["reviews"])


@api_router.get("", response_model=APIResponse[list[ReviewResponse]])
async def api_list_reviews(project_id: str, db: Session = Depends(get_db)):
    reviews = ReviewService.list_reviews(db, project_id)
    return APIResponse(data=reviews)


@api_router.get("/{review_id}", response_model=APIResponse[dict])
async def api_get_review(review_id: str, project_id: str, db: Session = Depends(get_db)):
    import json as j
    review = ReviewService.get_review(db, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    findings = []
    if review.findings and review.findings != '[]':
        try:
            findings = j.loads(review.findings)
        except (j.JSONDecodeError, ValueError):
            findings = []
    summary = {}
    if review.summary and review.summary != '{}':
        try:
            summary = j.loads(review.summary)
        except (j.JSONDecodeError, ValueError):
            summary = {}
    return APIResponse(data={"review": review, "findings": findings, "summary": summary})
```

- [ ] **Step 2: 在 `app/main.py` include**

```python
from app.routers.reviews import api_router as reviews_api
app.include_router(reviews_api)
```

- [ ] **Step 3: 创建 `tests/test_api_reviews.py`**

```python
from app.models.project import Project
from app.models.review import Review


class TestReviewsAPI:
    def _seed(self, db_session):
        db_session.add(Project(id="p1", title="Test", description="", genre=""))
        db_session.commit()

    def test_list_empty(self, client, db_session):
        self._seed(db_session)
        resp = client.get("/api/projects/p1/reviews")
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    def test_list_with_data(self, client, db_session):
        self._seed(db_session)
        db_session.add(Review(id="r1", project_id="p1", chapter_id="c1", review_type="batch",
                              summary="{}", findings="[]"))
        db_session.commit()

        resp = client.get("/api/projects/p1/reviews")
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["review_type"] == "batch"

    def test_get_detail(self, client, db_session):
        self._seed(db_session)
        db_session.add(Review(id="r2", project_id="p1", chapter_id="c1", review_type="batch",
                              summary='{"score": 8}', findings='[{"issue": "typo"}]'))
        db_session.commit()

        resp = client.get("/api/projects/p1/reviews/r2")
        assert resp.status_code == 200
        body = resp.json()["data"]
        assert body["summary"]["score"] == 8
        assert body["findings"][0]["issue"] == "typo"
```

- [ ] **Step 4: 运行测试并提交**

```bash
pytest tests/test_api_reviews.py -v
git add app/routers/reviews.py app/main.py tests/test_api_reviews.py
git commit -m "feat(api): add reviews JSON API endpoints with tests"
```

---

### Task 9: Config — JSON API 端点 + 测试

**Files:**
- Modify: `app/routers/config.py`
- Modify: `app/main.py`
- Create: `tests/test_api_config.py`

---

- [ ] **Step 1: 在 `app/routers/config.py` 末尾添加 api_router**

```python
from app.schemas.response import APIResponse


api_router = APIRouter(prefix="/api/config", tags=["config"])


@api_router.get("", response_model=APIResponse[dict])
async def api_get_config(db: Session = Depends(get_db)):
    cfg = ConfigService.get_all(db)
    return APIResponse(data=cfg)


@api_router.post("", response_model=APIResponse[dict])
async def api_save_config(body: dict, db: Session = Depends(get_db)):
    for key in ("llm_provider", "api_key", "base_url", "model", "host", "port"):
        if key in body:
            ConfigService.set(db, key, body[key])
    cfg = ConfigService.get_all(db)
    return APIResponse(data=cfg)
```

- [ ] **Step 2: 在 `app/main.py` include**

```python
from app.routers.config import api_router as config_api
app.include_router(config_api)
```

- [ ] **Step 3: 创建 `tests/test_api_config.py`**

```python
class TestConfigAPI:
    def test_get_config(self, client):
        resp = client.get("/api/config")
        assert resp.status_code == 200
        body = resp.json()
        assert body["message"] == "ok"
        assert isinstance(body["data"], dict)

    def test_save_and_get(self, client):
        resp = client.post("/api/config", json={"llm_provider": "openai"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["llm_provider"] == "openai"

        # Verify persisted
        resp = client.get("/api/config")
        assert resp.json()["data"]["llm_provider"] == "openai"
```

- [ ] **Step 4: 运行测试并提交**

```bash
pytest tests/test_api_config.py -v
git add app/routers/config.py app/main.py tests/test_api_config.py
git commit -m "feat(api): add config JSON API endpoints with tests"
```

---

### Task 10: OpenAPI spec 验证 + openapi-typescript 配置

**Files:**
- Create: `openapi-typescript.config.ts`（或 `openapitools.json`）

---

- [ ] **Step 1: 启动后端，验证 OpenAPI spec**

```bash
# 在一个终端启动后端
uvicorn app.main:app --port 8000 &

# 获取 spec，检查是否包含所有 JSON API 端点
curl -s http://localhost:8000/openapi.json | python -m json.tool | grep -E '"path|"/api/' | head -30
```

验证输出中包含所有 `/api/projects`、`/api/projects/{project_id}/outlines` 等路径。

```bash
# 终止后端进程
kill %1
```

- [ ] **Step 2: （可选）在同级目录下创建 openapi-typescript 配置文件供 Phase 2 使用**

```json
{
  "openapi-typescript": {
    "input": "http://localhost:8000/openapi.json",
    "output": "./types/api.d.ts"
  }
}
```

此文件将在 Phase 2（Next.js 项目搭建）时使用，Phase 1 只需确认 OpenAPI spec 可用。

- [ ] **Step 3: 运行全部测试，确保没有回归**

```bash
pytest tests/ -v
```
预期：所有测试 PASS（包括原有测试和新 JSON API 测试）

- [ ] **Step 4: 提交**

```bash
git add .
git commit -m "chore: verify OpenAPI spec and add openapi-typescript config"
```

---

### Task 11: 最终集成验证 + PR

---

- [ ] **Step 1: 在内存中验证 OpenAPI spec 包含所有路由**

```bash
# 启动后端
uvicorn app.main:app --port 8000 &
sleep 2

# 检查关键路径
echo "=== API 路由列表 ==="
curl -s http://localhost:8000/openapi.json | python3 -c "
import json, sys
spec = json.load(sys.stdin)
paths = list(spec.get('paths', {}).keys())
for p in sorted(paths):
    methods = list(spec['paths'][p].keys())
    print(f'{p:50s} {methods}')
"

# 验证所有 JSON API 端点
echo
echo "=== 测试 JSON API 端点 ==="
curl -s http://localhost:8000/api/projects | python3 -c "import json,sys; print('GET /api/projects:', json.load(sys.stdin)['message'])"
curl -s http://localhost:8000/api/styles | python3 -c "import json,sys; print('GET /api/styles:', json.load(sys.stdin)['message'])"
curl -s http://localhost:8000/api/config | python3 -c "import json,sys; print('GET /api/config:', json.load(sys.stdin)['message'])"
curl -s http://localhost:8000/api/ideas | python3 -c "import json,sys; print('GET /api/ideas:', json.load(sys.stdin)['message'])"

# 验证 HTML 端点仍然正常
echo
echo "=== 测试 HTML 端点 ==="
curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/
echo " GET /"
curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/projects/list
echo " GET /projects/list"
curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/styles
echo " GET /styles"

kill %1 2>/dev/null
```

确认输出：
- OpenAPI spec 包含所有 `/api/...` 路径
- 所有 JSON 端点返回 `{"message":"ok",...}`
- 所有 HTML 端点返回 200

- [ ] **Step 2: 运行完整测试套件**

```bash
pytest tests/ -v
```
确认全绿。

- [ ] **Step 3: 创建 PR**

```bash
git push -u origin refactor/phase1-api-backend
gh pr create --title "Phase 1: API-ify backend with JSON endpoints, CORS, and OpenAPI spec" \
  --body "$(cat <<'EOF'
## Summary

Phase 1 of the Next.js + FastAPI refactoring project. Adds JSON API layer alongside existing Jinja2 template endpoints.

### Changes

**Infrastructure**
- CORS middleware for Next.js dev server (`localhost:3000`)
- Auth middleware skeleton (`app/middleware/auth.py`)
- Unified `APIResponse[T]` wrapper (`app/schemas/response.py`)

**JSON API Endpoints** (`/api/...`)
- Projects: CRUD (list, create, get, delete)
- Outlines: CRUD + reorder + tree
- Settings: CRUD + reorder + category filter
- Chapters: CRUD + reorder
- Styles: list + delete
- Ideas: CRUD + reorder
- Reviews: list + detail (with parsed JSON fields)
- Config: get + save

**Testing**
- 8 new test files covering all JSON API endpoints
- All existing tests pass unchanged
- OpenAPI spec verified with all endpoints

### Test Plan
- `pytest tests/ -v` — all passing
- Start server, verify `GET /api/projects` returns JSON
- Start server, verify `GET /` returns HTML (backward compat)
EOF
)"
```

---

## 计划自审

**Spec 覆盖检查：**
- CORS ✅ (Task 1)
- 认证骨架 ✅ (Task 1)
- 统一 JSON 响应基类 ✅ (Task 1)
- 每个路由都添加了 JSON API 端点 ✅ (Tasks 2-9)
- 所有 endpoint 标注了 response_model ✅
- OpenAPI spec 验证 ✅ (Task 10)
- openapi-typescript 配置文件 ✅ (Task 10)
- JSON API 测试 ✅ (Tasks 2-9 各包含测试)

**占位符检查：** 无 TBD/TODO/vague_placeholder — 所有代码完整，可直接使用。

**类型一致性检查：** 所有 Response schema 使用了 `from_attributes = True` Config，与现有 SQLAlchemy 模型一致。API 响应路径（`/api/projects/{id}` / `/api/projects/{pid}/outlines/{id}` 等）在所有 router 中遵循统一模式。

**SSE 端点：** agent.py 和 outline_gen.py 的 SSE 端点保持不动（已返回 JSON/SSE），无需修改。
