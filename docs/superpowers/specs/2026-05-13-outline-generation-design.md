# AI Outline Generation — Design Spec

> 版本：v1.0
> 日期：2026-05-13
> 状态：设计完成，待实现

---

## 1. 概述

在已有的大纲管理模块基础上，增加 AI 生成能力。用户提供故事描述和设定参考，AI 逐层生成卷→章→节→正文，每步用户确认后写入。

### 生成层次

```
故事描述 ─→ 卷列表 ─→ 章节列表 ─→ 细纲列表 ─→ 章节正文
```

每一层都可独立触发，上层生成后下层可基于上层内容继续生成。

---

## 2. 后端设计

### 2.1 OutlineGenerationService

新建 `app/services/outline_gen_service.py`，与现有 `OutlineService` 分离。每个生成方法返回结构化数据（而非直接写 DB），用户确认后再通过 `OutlineService` 写入。

```python
class OutlineGenerationService:
    @staticmethod
    async def generate_volumes(db, project_id, story_desc, setting_ids) -> list[dict]
        # 注入设定集 → LLM → 返回 [{title, summary}, ...]

    @staticmethod
    async def generate_chapters(db, project_id, volume_id, volume_title, volume_summary) -> list[dict]
        # 基于卷描述 → LLM → 返回 [{title, summary}, ...]

    @staticmethod
    async def generate_sections(db, project_id, chapter_id, chapter_title, chapter_summary) -> list[dict]
        # 基于章描述 → LLM → 返回 [{title, summary, notes}, ...]

    @staticmethod
    async def generate_content(db, project_id, section) -> str
        # 基于细纲 → LLM → 返回正文
```

### 2.2 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/project/{pid}/outline/generate/volumes` | 生成卷 |
| POST | `/project/{pid}/outline/generate/chapters` | 生成章 |
| POST | `/project/{pid}/outline/generate/sections` | 生成细纲 |
| POST | `/project/{pid}/outline/generate/content` | 生成正文 |
| POST | `/project/{pid}/outline/generate/confirm` | 确认写入 |

`/confirm` 接收前端编辑后的数据，批量调用 `OutlineService.create` 写入。

### 2.3 Prompt 文件

```
app/llm/prompts/
├── outline_gen_volume.txt     # 卷生成
├── outline_gen_chapter.txt    # 章节生成
├── outline_gen_section.txt    # 细纲生成
└── outline_gen_content.txt    # 正文生成
```

每个 prompt 含 system prompt + JSON 输出格式约束。使用流式端点 StreamingResponse 输出。

---

## 3. 前端设计

### 3.1 入口

大纲页面顶部新增「AI 生成大纲」按钮，模态框内容包括：

```
┌──────────────────────────────────────────┐
│  AI 生成大纲                              │
│                                          │
│  故事描述 *                               │
│  ┌────────────────────────────────────┐  │
│  │ 输入你的故事梗概...                  │  │
│  └────────────────────────────────────┘  │
│                                          │
│  参考设定                                │
│  ☑ 人物: 林墨、王城                      │
│  ☑ 世界观: 特殊事件调查局                 │
│  ☐ 组织: ...                             │
│  ☑ 全部选中                              │
│                                          │
│  生成范围                                │
│  ○ 仅卷结构  ○ 卷+章  ● 完整(卷+章+细纲) │
│                                          │
│            [取消]  [开始生成]              │
└──────────────────────────────────────────┘
```

### 3.2 生成结果展示

流式输出逐条渲染，完成后显示确认界面：

```
┌─ 生成结果 ──────────────────────────┐
│                                     │
│  第一卷：迷雾降临                    │
│  概要：林墨收到神秘信件...            │
│  ┌─ 第一章：不速之客 ────────────┐  │
│  │  概要：深夜来访...              │  │
│  │  ├ 场景：拆信                   │  │
│  │  ├ 场景：调查                   │  │
│  │  └ 场景：遇袭                   │  │
│  └───────────────────────────────┘  │
│  ┌─ 第二章：暗流涌动 ────────────┐  │
│  │  ...                           │  │
│  └───────────────────────────────┘  │
│                                     │
│  [编辑]                    [确认写入] │
└─────────────────────────────────────┘
```

### 3.3 逐层生成

每个卷条目旁显示「▼ AI 生成」下拉操作：
- 生成章节 → 调用 chapters 接口
- 生成细纲 → 调用 sections 接口

---

## 4. 不实现的范围

- 正文生成只做单节→单章，不做全书一次性生成
- 不做生成前后的版本对比
- 不保存生成历史（只保存最终确认结果）
