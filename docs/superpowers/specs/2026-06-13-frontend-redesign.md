# 前端现代化改版 —— 设计规格 (v2)

## 概述

对 Novel Forge 前端进行全面视觉改版，从基础的 shadcn 默认灰色风格升级为 **深邃现代 (Dark-First Modern)** 设计语言，同时支持深色/暖纸双模式。

## 设计方向

| 维度 | 决策 |
|------|------|
| **风格** | 深邃现代 — 暗色优先，高对比度，大胆强调色 |
| **强调色** | 紫色 — 代表创意、想象力、神秘感 |
| **卡片等级** | Glass（毛玻璃） + Solid（实心）两种等级，按场景选用 |
| **侧边栏** | 可折叠 — 默认展开，可折叠为 48px 图标栏 |
| **模式策略** | 三态：暗色(默认) / 暖纸(sepia) / 跟随系统 |
| **跟随系统映射** | 系统 Light → Sepia，系统 Dark → 暗色 |

## 设计系统

### 1. 完整色彩体系

#### 基础色板 — Dark Mode（默认）

```css
:root, .dark {
  /* 背景层级 */
  --bg-primary: #0b0b0e;      /* 最底层背景 */
  --bg-secondary: #0e0e12;    /* 次级背景（侧边栏等） */
  --bg-elevated: #141418;     /* 卡片/弹窗/下拉菜单 */
  --bg-hover: #1c1c22;        /* hover 态背景 */
  --bg-input: #18181c;        /* 输入框背景 */

  /* 边框 */
  --border-subtle: #1c1c22;   /* 极淡边框（卡片默认） */
  --border-default: #27272e;  /* 标准边框（输入框等） */
  --border-strong: #3f3f46;   /* 强调边框 */

  /* 文字 */
  --text-primary: #f4f4f5;    /* 主文字/标题 */
  --text-secondary: #c4c4c8;  /* 次级文字/正文 */
  --text-tertiary: #71717a;   /* 辅助文字/说明 */
  --text-muted: #52525b;      /* 禁用态/占位符 */
  --text-inverse: #0b0b0e;    /* 反色文字（用在彩色背景上） */
}
```

**写作编辑器专用背景（覆盖）：**

```css
--editor-bg: #111114;         /* 写作区背景 — 深灰而非纯黑 */
--editor-text: #d4d4d8;       /* 写作区正文 */
--editor-cursor: #a78bfa;     /* 光标色（紫色） */
```

#### 基础色板 — Sepia Warm Mode

```css
.sepia {
  --bg-primary: #f2ede5;      /* 暖纸底色 */
  --bg-secondary: #ece6dc;    /* 次级背景 */
  --bg-elevated: #ffffffd4;   /* 卡片/弹窗（半透明白） */
  --bg-hover: #e8e0d4;        /* hover 态 */
  --bg-input: #ffffff;        /* 输入框背景 */

  --border-subtle: #e4dcd0;   /* 极淡边框 */
  --border-default: #d4ccc0;  /* 标准边框 */
  --border-strong: #b4aca0;   /* 强调边框 */

  --text-primary: #2d2a24;    /* 主文字 */
  --text-secondary: #4a4640;  /* 次级文字 */
  --text-tertiary: #8a847c;   /* 辅助文字 */
  --text-muted: #b4aca0;      /* 禁用态 */
  --text-inverse: #ffffff;

  --editor-bg: #ffffffd0;     /* 写作区 */
  --editor-text: #2d2a24;
  --editor-cursor: #7c3aed;
}
```

#### 强调色 — 紫色（双模式适配）

```css
:root, .dark {
  --accent-base: #7c3aed;              /* 基础紫 */
  --accent-hover: #8b5cf6;             /* hover 紫 */
  --accent-active: #6d28d9;            /* 点击态 */
  --accent-subtle: rgba(124,58,237,0.10);  /* 极淡紫底 */
  --accent-border: rgba(124,58,237,0.25);  /* 紫色边框 */
  --accent-glow: rgba(124,58,237,0.12);    /* hover 发光 */
  --accent-text: #a78bfa;              /* 紫色文字（可读性保证） */
  --gradient-accent: linear-gradient(135deg, #7c3aed, #a855f7);
}

.sepia {
  --accent-base: #7c3aed;
  --accent-hover: #6d28d9;
  --accent-active: #5b21b6;
  --accent-subtle: rgba(124,58,237,0.08);
  --accent-border: rgba(124,58,237,0.20);
  --accent-glow: rgba(124,58,237,0.08);
  --accent-text: #6d28d9;
}
```

#### 状态色

```css
:root, .dark {
  --success-base: #22c55e;
  --success-subtle: rgba(34,197,94,0.12);
  --success-text: #4ade80;
  --success-border: rgba(34,197,94,0.25);

  --warning-base: #f59e0b;
  --warning-subtle: rgba(245,158,11,0.12);
  --warning-text: #fbbf24;
  --warning-border: rgba(245,158,11,0.25);

  --danger-base: #ef4444;
  --danger-subtle: rgba(239,68,68,0.12);
  --danger-text: #f87171;
  --danger-border: rgba(239,68,68,0.25);

  --info-base: #3b82f6;
  --info-subtle: rgba(59,130,246,0.12);
  --info-text: #60a5fa;
  --info-border: rgba(59,130,246,0.25);
}

.sepia {
  --success-base: #16a34a;
  --success-subtle: rgba(22,163,74,0.10);
  --success-text: #15803d;
  --success-border: rgba(22,163,74,0.20);

  --warning-base: #d97706;
  --warning-subtle: rgba(217,119,6,0.10);
  --warning-text: #b45309;
  --warning-border: rgba(217,119,6,0.20);

  --danger-base: #dc2626;
  --danger-subtle: rgba(220,38,38,0.10);
  --danger-text: #b91c1c;
  --danger-border: rgba(220,38,38,0.20);

  --info-base: #2563eb;
  --info-subtle: rgba(37,99,235,0.10);
  --info-text: #1d4ed8;
  --info-border: rgba(37,99,235,0.20);
}
```

### 2. 排版

```css
/* 沿用 Geist 字体 (已配置) */
--font-sans: 'Geist', system-ui, sans-serif;
--font-mono: 'Geist Mono', monospace;

/* 字号层级 */
--text-xs: 0.7rem;
--text-sm: 0.8rem;
--text-base: 0.9rem;
--text-lg: 1rem;
--text-xl: 1.25rem;
--text-2xl: 1.5rem;
--text-3xl: 1.75rem;

/* 行高 */
--leading-relaxed: 1.75;  /* 正文 */
--leading-snug: 1.4;      /* 标题 */
```

### 3. 间距与圆角

```css
--radius-xs: 0.25rem;
--radius-sm: 0.375rem;
--radius-md: 0.5rem;
--radius-lg: 0.75rem;
--radius-xl: 1rem;

--spacing-xs: 0.25rem;
--spacing-sm: 0.5rem;
--spacing-md: 0.75rem;
--spacing-lg: 1rem;
--spacing-xl: 1.5rem;
--spacing-2xl: 2rem;
```

### 4. 卡片等级规范

卡片分两种等级，按场景选用，不混用：

| 等级 | 实现 | 适用场景 | 原因 |
|------|------|----------|------|
| **Solid** | `background: var(--bg-elevated)` + `border: 1px solid var(--border-subtle)` | Dashboard 项目卡片、Ideas 卡片、Styles 卡片 | 渲染开销低，Sepia 模式下视觉一致 |
| **Glass** | `background: rgba(255,255,255,0.03)` + `backdrop-filter: blur(6px)` | Chat 气泡、浮动面板、hover 高亮 | 少量使用，提升层次感 |

**Hover 效果（统一）：**

```css
.card-solid:hover,
.card-glass:hover {
  border-color: var(--accent-border);
  box-shadow: 0 0 16px var(--accent-glow);
}
```

### 5. 全局 CSS 变更方案

- 通过 `@theme inline {}` 将以上 CSS 变量注册为 Tailwind 主题色
- 在 `globals.css` 中定义三组选择器：`:root, .dark {}` / `.sepia {}`
- 主题切换通过 `<html data-theme="dark|sepia|system">` 控制
- `.dark` 选择器优先级低于 `[data-theme]`，跟随系统模式下探测 `prefers-color-scheme`
- **技术实现使用 `var(--token)` 而非 `theme()` 函数**，确保运行时主题切换正确

## 页面设计

### 1. 主布局

```
┌──────────────────────────────────────┐
│  Sidebar (240px / 48px)  │  Content  │
│                          │  (flex-1) │
│  ▸ Logo + 名称            │  overflow │
│  ▸ 分隔线                  │  -auto    │
│  ▸ 导航项(图标+文字)       │           │
│  ▸ 分隔线                  │           │
│  ▸ 主题切换 / 折叠按钮     │           │
└──────────────────────────────────────┘
```

- 侧边栏背景 `var(--bg-secondary)`
- 内容区背景 `var(--bg-primary)`
- 侧边栏动画：`width` transition 250ms ease

### 2. 侧边栏折叠态 (48px)

| 元素 | 展开态 (240px) | 折叠态 (48px) |
|------|----------------|----------------|
| Logo | 图标 + "Novel Forge" 文字 | 仅图标，居中 |
| 导航项 | 图标 + 标签文字 | 仅图标，居中 |
| 激活态 | `--accent-subtle` 背景 + `--accent-text` 文字 | 同左 + 左侧 2px 紫色竖线 |
| Tooltip | 不显示 | hover 时显示标签文字 |
| 主题切换 | 下拉菜单（暗色/暖纸/跟随） | 图标按钮，点击弹出小菜单 |
| 折叠按钮 | 文字 "收起" + 图标 | 图标 "展开" |

导航项 Tooltip 实现：使用 CSS `::after` 伪元素，hover 200ms delay 后出现。

### 3. 响应式布局规范

| 断点 | 宽度 | 侧边栏 | Dashboard 网格 | Writer | Chat | 移动端行为 |
|------|------|--------|----------------|--------|------|-----------|
| **Desktop** | ≥1024px | 展开 (240px) | 3 列 | 章节栏 224px + 编辑器 | 消息 + 侧栏 | 正常布局 |
| **Tablet** | 768–1023px | 折叠 (48px) | 2 列 | 章节栏变为左侧按钮弹出 | 消息全宽 | 侧边栏自动折叠 |
| **Mobile** | <768px | Drawer (overlay) | 1 列 | 隐藏章节栏，底部按钮切换 | 消息全宽，输入框固定底部 | Dashboard Drawer 代替侧边栏 |

**Dashboard 网格断点细化：**

```css
grid-template-columns: repeat(3, 1fr);  /* ≥1024px */
grid-template-columns: repeat(2, 1fr);  /* 768–1023px */
grid-template-columns: 1fr;             /* <768px */
```

**移动端 Drawer：**
- 点击汉堡图标从左侧滑出
- 遮罩层 (`bg-black/50`)
- Drawer 宽度 280px
- `transform: translateX(-100%)` 隐藏 → `translateX(0)` 显示

### 4. 工作台 (Dashboard)

- 页面标识: 紫色 label + 标题
- 导航卡片网格 (3→2→1 列响应式)，使用 **Solid** 卡片等级
- 每张卡片：图标容器（圆角，带场景色背景） + 标题 + 描述
- 项目列表区域：
  - 顶部：标题 "项目" + 项目计数 + "新建项目" 按钮
  - 网格 (3→2→1 列)，Solid 卡片
  - 每张卡片：类型标签（彩色） + 标题 + 简介(line-clamp-2) + 状态徽章 + 更新时间 + 删除按钮(hover 出现)
  - 空态：居中图标 + "还没有项目，创建一个吧"

**类型标签色映射：**

| 类型 | Dark 色 | Sepia 色 |
|------|---------|----------|
| 科幻 | `#a78bfa` 紫 | `#7c3aed` |
| 奇幻 | `#fbbf24` 黄 | `#d97706` |
| 悬疑 | `#34d399` 绿 | `#16a34a` |
| 言情 | `#f472b6` 粉 | `#db2777` |
| 历史 | `#fb923c` 橙 | `#ea580c` |
| 默认 | `#a1a1aa` 灰 | `#71717a` |

### 5. 写作编辑器 (Writer)

- **背景**: `var(--editor-bg)` = `#111114`（深灰，非纯黑）
- **内容区**: 居中 `max-width: 42rem`，padding 2rem 3rem
- **顶栏**: 左侧折叠章节栏按钮 | 居中: 章节名 · 字数 | 右侧: 搜索 / AI 辅助 / 主题切换
- **章节结构标识**: 紫色竖线(`2px`，`--accent-base`) + 卷/部标签（`--text-tertiary`，小字）
- **章节标题**: `font-size: 1.75rem`，`font-weight: 700`，`letter-spacing: -0.02em`
- **正文**: `font-size: 0.95rem`，`line-height: 1.85`，`color: var(--editor-text)`，首行缩进 `2em`
- **AI 建议嵌入卡片**: Solid 等级，左侧 `3px` 紫色实线边框 + `--accent-subtle` 背景，圆角 `0.5rem`
- **底栏**: 字数统计 · 阅读时间 | 自动保存状态，`--text-muted` 小字
- **章节侧边栏**: 独立于全局侧边栏，宽 224px，`--bg-secondary` 背景

**章节侧边栏响应式：**
- Desktop: 固定 224px 显示
- Tablet: 默认隐藏，点击顶栏按钮弹出 overlay
- Mobile: 默认隐藏，底部浮动按钮切换

### 6. Agent 助手 (Chat) — 信息架构

#### 消息类型

| 类型 | 视觉 | 说明 |
|------|------|------|
| user_message | 紫色实心气泡，右对齐 | 用户发送的文本 |
| assistant_message | Glass 气泡，左对齐 | AI 回复文本 |
| tool_call | 折叠卡片，可展开 | 函数调用记录 |
| tool_result | 代码块样式，缩进 | 调用返回结果 |
| reasoning | 半透明折叠区域 | 推理过程/思考链 |
| system | 居中迷你徽章 | 系统通知/错误 |
| streaming | 跳动紫点动画 | 流式响应占位 |

#### 长消息处理

- 默认显示全部内容，不截断
- 超过 600px 高度的消息右上角显示 "📌 折叠" 按钮
- 折叠后显示前 3 行 + "展开全部 (N 行)" 链接
- 代码块默认不折叠（代码应完整可见）

#### Markdown 渲染规则

AI 回复支持完整 Markdown：

| 元素 | 样式 |
|------|------|
| 标题 (h1-h3) | `--text-primary`，粗体，层级间距 |
| 段落 | `--text-secondary`，行高 1.75 |
| 粗体/斜体 | 标准 markdown |
| 列表 (ul/ol) | 缩进 + 间距 0.35rem |
| 代码行 (inline) | `--bg-elevated` 背景，`--accent-text` 文字，圆角 0.25rem |
| 代码块 (fenced) | 深色画布 `#0b0b0e`，等宽字体，行号可选，带语言标签和复制按钮 |
| 引用块 | 左侧 3px `--accent-base` 竖线 + 斜体 |
| 分割线 | `--border-subtle`，my 1rem |
| 链接 | `--accent-text`，hover 下划线 |

**代码块样式：**

```css
.chat-code-block {
  background: #0b0b0e;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  font-size: 0.8rem;
  line-height: 1.6;
}
.chat-code-header {
  display: flex;
  justify-content: space-between;
  padding: 0.35rem 0.75rem;
  border-bottom: 1px solid var(--border-subtle);
  font-size: 0.7rem;
  color: var(--text-tertiary);
}
```

#### 推理过程区域 (Reasoning)

- 默认折叠，显示 "🤔 推理过程" 徽章
- 展开后半透明背景 (`--accent-subtle`)，灰色文字，斜体
- 与主回复之间用细分隔线

#### 输入区

- 嵌入在底部固定栏中
- 圆角容器 `border-radius: var(--radius-lg)`，`background: var(--bg-input)`，`border: 1px solid var(--border-default)`
- 左侧可选快捷操作图标
- 输入框 `flex: 1`，`background: transparent`
- 右侧紫色发送按钮 (`--accent-base`，disabled 时 `--text-muted`)
- Input 上方可显示上下文提示（如 "正在基于 第3章 对话..."）

#### 空态

- 紫色渐变圆形（`width: 4rem`，`height: 4rem`，`--gradient-accent`）
- 标题 + 引导文案
- `/brainstorm` 以代码块高亮形式呈现

### 7. 灵感 (Ideas)

- 快速录入行: 标题 Input + 内容 Input + 紫色添加按钮
- 卡片网格 (3→2→1 列响应式)，使用 **Solid** 卡片等级
- 卡片：琥珀色灯泡图标 + 标题 + 内容(line-clamp-3) + hover 显示删除按钮

### 8. 文风库 (Styles)

- 顶部：标题 + 导入按钮 (outline variant)
- 卡片网格 (2→1 列响应式)，Solid 卡片
- 卡片：紫色调图标 + 名称 + 来源标签 + 分析(可滚动 `max-h: 6rem`)
- hover 显示删除按钮

### 9. 配置 (Config)

- 双列表单 (`sm:grid-cols-2`，Mobile 单列)
- API Key 字段使用 `type="password"`
- 保存按钮 + 成功 toast（绿色 `--success-text`）

### 10. 项目详情页

- 返回按钮 + 项目标题 + 类型标签 + 状态 + 创建时间
- 子功能卡片网格 (2 列)，Solid 卡片
- 子卡片：标题 + 简短描述

## 模式切换策略

### 三态定义

| 用户选择 | 实际效果 | 实现方式 |
|----------|----------|----------|
| `dark` | 强制暗色 | `<html data-theme="dark">` |
| `sepia` | 强制暖纸 | `<html data-theme="sepia">` |
| `system` | 跟随系统偏好 | JS 监听 `prefers-color-scheme`，系统 Dark → dark，系统 Light → sepia |

**关键规则**：`system` 状态下，系统 Light 映射为 sepia 而非纯白，保持"无纯白模式"的承诺。

### 持久化

- 用户选择存入 `localStorage` key: `novel-forge-theme`
- 页面加载时从 localStorage 读取，无存储则默认 `dark`
- `system` 模式需要额外监听 `matchMedia('prefers-color-scheme')` 的 change 事件

## 交互状态

### 加载态
- 所有列表/详情页: 居中紫色旋转图标 (替换原先 `text-zinc-400`)
- 按钮: disabled 态显示 `--text-muted`，`opacity-50`，`cursor-not-allowed`
- Skeleton: 可选，不强制要求

### 空态
- 统一模式: 居中圆形容器 + emoji/图标 + 文字提示
- 列表页: 通用空态组件，可复用

### 错误态
- 404: 基本布局 + 返回链接
- API 错误: inline error banner，浅色背景 + 左侧红色竖线 + 错误信息 + 重试按钮

## 动画与过渡

```css
:root {
  --transition-fast: 150ms ease;
  --transition-normal: 250ms ease;
}

/* 卡片 hover */
.card-solid, .card-glass {
  transition: border-color var(--transition-normal),
              box-shadow var(--transition-normal);
}

/* 侧边栏折叠 */
.sidebar {
  transition: width var(--transition-normal);
}

/* 页面内容切换 */
main {
  transition: opacity 200ms ease;
}

/* Chat 消息入场 */
@keyframes message-in {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}
.chat-message {
  animation: message-in 250ms ease both;
}
```

## 实现约束

- **无新增 npm 包依赖** — 全部通过 CSS 变量 + TailwindCSS v4 实现
- 所有颜色引用使用 `var(--token)` 形式，确保运行时主题切换
- TailwindCSS v4 的 `@theme inline {}` 中注册 CSS 变量引用（而非硬编码色值），形如：
  ```css
  @theme inline {
    --color-accent: var(--accent-base);
    --color-background: var(--bg-primary);
  }
  ```
- 主题切换不依赖 Tailwind 的 `dark:` 变体，而是通过 `data-theme` 属性 + CSS 变量覆盖
- 所有页面需覆盖 Loading / Empty / Error / Success 四种状态
- 键盘可访问性: 所有交互元素可 focus 且有 visible focus ring
