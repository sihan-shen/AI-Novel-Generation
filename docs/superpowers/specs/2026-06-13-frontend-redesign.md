# 前端现代化改版 —— 设计规格 (v3)

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

设计系统分三层：

```
基础 Token  →  语义 Token  →  组件引用
(色板/圆角)    (用途命名)     (直接使用)
```

- **基础 Token**：定义纯粹的色值、尺寸、间距
- **语义 Token**：将基础 Token 映射到用途（如 `--surface-card`、`--button-primary-bg`）
- **组件引用**：组件直接使用语义 Token，未来改色只需调整语义映射

### 1. 基础色板

#### Dark Mode（默认）

```css
:root, .dark {
  /* 背景层级 */
  --bg-base: #0b0b0e;         /* 最底层背景 */
  --bg-base-secondary: #0e0e12;  /* 次级背景 */
  --bg-elevated: #141418;     /* 卡片/弹窗/下拉菜单 */
  --bg-elevated-hover: #1c1c22;  /* 卡片/弹窗 hover */
  --bg-input: #18181c;        /* 输入框背景 */

  /* 边框 */
  --border-subtle: #1c1c22;   /* 极淡边框 */
  --border-default: #27272e;  /* 标准边框 */
  --border-strong: #3f3f46;   /* 强调边框 */

  /* 文字 */
  --text-primary: #f4f4f5;
  --text-secondary: #c4c4c8;
  --text-tertiary: #71717a;
  --text-muted: #52525b;
  --text-inverse: #0b0b0e;

  /* 阴影 */
  --shadow-card: 0 1px 3px rgba(0,0,0,0.4);
  --shadow-dialog: 0 8px 32px rgba(0,0,0,0.6);
}
```

#### Sepia Warm Mode

```css
.sepia {
  --bg-base: #f2ede5;
  --bg-base-secondary: #ece6dc;
  --bg-elevated: #ffffffd4;
  --bg-elevated-hover: #e8e0d4;
  --bg-input: #ffffff;

  --border-subtle: #e4dcd0;
  --border-default: #d4ccc0;
  --border-strong: #b4aca0;

  --text-primary: #2d2a24;
  --text-secondary: #4a4640;
  --text-tertiary: #8a847c;
  --text-muted: #b4aca0;
  --text-inverse: #ffffff;

  --shadow-card: 0 1px 3px rgba(0,0,0,0.06);
  --shadow-dialog: 0 8px 32px rgba(0,0,0,0.10);
}
```

#### 强调色 — 紫色

```css
:root, .dark {
  --accent-base: #7c3aed;
  --accent-hover: #8b5cf6;
  --accent-active: #6d28d9;
  --accent-subtle: rgba(124,58,237,0.10);
  --accent-border: rgba(124,58,237,0.25);
  --accent-glow: rgba(124,58,237,0.12);
  --accent-text: #a78bfa;
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
  --success-base: #22c55e;    --success-subtle: rgba(34,197,94,0.12);
  --success-text: #4ade80;    --success-border: rgba(34,197,94,0.25);
  --warning-base: #f59e0b;   --warning-subtle: rgba(245,158,11,0.12);
  --warning-text: #fbbf24;   --warning-border: rgba(245,158,11,0.25);
  --danger-base: #ef4444;    --danger-subtle: rgba(239,68,68,0.12);
  --danger-text: #f87171;    --danger-border: rgba(239,68,68,0.25);
  --info-base: #3b82f6;      --info-subtle: rgba(59,130,246,0.12);
  --info-text: #60a5fa;      --info-border: rgba(59,130,246,0.25);
  --processing-base: #8b5cf6;   --processing-subtle: rgba(139,92,246,0.12);
  --processing-text: #a78bfa;   --processing-border: rgba(139,92,246,0.25);
}

.sepia {
  --success-base: #16a34a;    --success-subtle: rgba(22,163,74,0.10);
  --success-text: #15803d;    --success-border: rgba(22,163,74,0.20);
  --warning-base: #d97706;   --warning-subtle: rgba(217,119,6,0.10);
  --warning-text: #b45309;   --warning-border: rgba(217,119,6,0.20);
  --danger-base: #dc2626;    --danger-subtle: rgba(220,38,38,0.10);
  --danger-text: #b91c1c;    --danger-border: rgba(220,38,38,0.20);
  --info-base: #2563eb;      --info-subtle: rgba(37,99,235,0.10);
  --info-text: #1d4ed8;      --info-border: rgba(37,99,235,0.20);
  --processing-base: #7c3aed;   --processing-subtle: rgba(124,58,237,0.08);
  --processing-text: #6d28d9;   --processing-border: rgba(124,58,237,0.20);
}
```

### 2. 语义 Token

语义 Token 层将基础色板按用途命名，组件直接引用这一层。

```css
/* 表面层级 */
--surface-page: var(--bg-base);
--surface-sidebar: var(--bg-base-secondary);
--surface-card: var(--bg-elevated);
--surface-dialog: var(--bg-elevated);
--surface-tooltip: var(--bg-elevated);
--surface-input: var(--bg-input);

/* 按钮 */
--button-primary-bg: var(--accent-base);
--button-primary-text: #ffffff;
--button-primary-hover: var(--accent-hover);
--button-primary-active: var(--accent-active);
--button-outline-border: var(--border-default);
--button-outline-text: var(--text-primary);
--button-outline-hover-bg: var(--bg-elevated-hover);
--button-ghost-text: var(--text-secondary);
--button-ghost-hover-bg: var(--bg-elevated-hover);

/* 输入框 */
--input-bg: var(--bg-input);
--input-border: var(--border-default);
--input-text: var(--text-primary);
--input-placeholder: var(--text-muted);
--input-focus-ring: var(--accent-base);
--input-focus-border: var(--accent-border);

/* 导航 */
--nav-item-text: var(--text-tertiary);
--nav-item-hover-bg: var(--bg-elevated);
--nav-item-active-bg: var(--accent-subtle);
--nav-item-active-text: var(--accent-text);
--nav-item-active-indicator: var(--accent-base);

/* 标签 (Badge) */
--badge-default-bg: var(--bg-elevated-hover);
--badge-default-text: var(--text-secondary);
--badge-success-bg: var(--success-subtle);
--badge-success-text: var(--success-text);
--badge-warning-bg: var(--warning-subtle);
--badge-warning-text: var(--warning-text);
--badge-danger-bg: var(--danger-subtle);
--badge-danger-text: var(--danger-text);
--badge-processing-bg: var(--processing-subtle);
--badge-processing-text: var(--processing-text);

/* 消息气泡 (Chat) */
--bubble-user-bg: var(--accent-base);
--bubble-user-text: #ffffff;
--bubble-assistant-bg: rgba(255,255,255,0.03);
--bubble-assistant-border: rgba(255,255,255,0.06);

/* 分隔线 */
--separator: var(--border-subtle);
```

### 3. Focus / Accessibility 体系

```css
/* 全局 focus-visible 环 — 统一所有组件 */
--focus-ring: rgba(124,58,237,0.45);

/* 应用方式（全局一次性定义，无需每组件写） */
*:focus-visible {
  outline: none;
  box-shadow: 0 0 0 3px var(--focus-ring);
}

/* 鼠标点击时不显示 focus ring */
*:focus:not(:focus-visible) {
  outline: none;
  box-shadow: none;
}
```

### 4. 排版

```css
--font-sans: 'Geist', system-ui, sans-serif;
--font-mono: 'Geist Mono', monospace;

--text-xs: 0.7rem;
--text-sm: 0.8rem;
--text-base: 0.9rem;
--text-lg: 1rem;
--text-xl: 1.25rem;
--text-2xl: 1.5rem;
--text-3xl: 1.75rem;

--leading-relaxed: 1.75;  /* 正文 */
--leading-snug: 1.4;      /* 标题 */
```

### 5. 间距与圆角

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

### 6. 卡片等级

| 等级 | 实现 | 适用场景 |
|------|------|----------|
| **Solid** | `background: var(--surface-card)` `border: 1px solid var(--border-subtle)` `box-shadow: var(--shadow-card)` | Dashboard 项目卡片、Ideas、Styles、Dialog |
| **Glass** | `background: var(--bubble-assistant-bg)` `backdrop-filter: blur(6px)` `border: 1px solid var(--bubble-assistant-border)` | Chat 气泡、浮动面板 |

**Hover（统一）：**

```css
.card-solid:hover,
.card-glass:hover {
  border-color: var(--accent-border);
  box-shadow: 0 0 16px var(--accent-glow);
}
```

### 7. 组件级规范

#### Button

| 变体 | 背景 | 文字 | Hover | 禁用 |
|------|------|------|-------|------|
| **primary** | `--button-primary-bg` | `--button-primary-text` | `--button-primary-hover` | `opacity: 0.5`，无 hover |
| **outline** | transparent | `--button-outline-text` | `--button-outline-hover-bg` | 同上 |
| **ghost** | transparent | `--button-ghost-text` | `--button-ghost-hover-bg` | 同上 |

- 圆角：`var(--radius-md)`
- 字号：`var(--text-sm)`，`font-weight: 500`
- 尺寸：h-8（默认）/ h-7（sm）/ h-9（lg）/ h-8（icon）
- 禁用态：`cursor-not-allowed`，无 hover 效果
- 加载态：前置 spinner，文字不变

#### Input / Textarea

- 背景：`var(--input-bg)`
- 边框：`var(--input-border)`
- 文字：`var(--input-text)`
- 占位符：`var(--input-placeholder)`
- Focus：`var(--input-focus-border)` + `box-shadow: 0 0 0 3px var(--focus-ring)`
- 圆角：`var(--radius-md)`
- 禁用态：`opacity: 0.5`
- 错误态：边框 `var(--danger-base)`，底部可接错误文字 `var(--danger-text)`

#### Badge（标签/徽章）

| 用途 | 背景 | 文字 |
|------|------|------|
| 默认 | `--badge-default-bg` | `--badge-default-text` |
| 成功 | `--badge-success-bg` | `--badge-success-text` |
| 警告 | `--badge-success-bg` | `--badge-warning-text` |
| 错误 | `--badge-danger-bg` | `--badge-danger-text` |
| 处理中 | `--badge-processing-bg` | `--badge-processing-text` |

- 圆角：`var(--radius-sm)`（pill 形），`padding: 0.15rem 0.5rem`
- 字号：`var(--text-xs)`

#### Dialog / Sheet

- 背景：`var(--surface-dialog)`
- 边框：`var(--border-subtle)`
- 阴影：`var(--shadow-dialog)`
- 圆角：`var(--radius-xl)`
- 遮罩：`rgba(0,0,0,0.5)`（dark 模式），`rgba(0,0,0,0.15)`（sepia 模式）

#### Dropdown / Select

- 触发态：同 button
- 菜单面板：`var(--surface-dialog)` + `var(--shadow-dialog)` + `var(--radius-md)`
- 菜单项：hover `var(--bg-elevated-hover)`，active `var(--accent-subtle)`
- 分隔线：`var(--separator)`

#### Separator

- 颜色：`var(--separator)`
- 高度：`1px`

### 8. 标签颜色算法

项目类型不硬编码映射。改为**标签颜色池 + 哈希分配**：

```ts
const TAG_COLORS = [
  { dark: '#a78bfa', sepia: '#7c3aed' },  // 紫
  { dark: '#fbbf24', sepia: '#d97706' },  // 黄
  { dark: '#34d399', sepia: '#16a34a' },  // 绿
  { dark: '#f472b6', sepia: '#db2777' },  // 粉
  { dark: '#fb923c', sepia: '#ea580c' },  // 橙
  { dark: '#60a5fa', sepia: '#2563eb' },  // 蓝
  { dark: '#818cf8', sepia: '#4f46e5' },  // 靛
  { dark: '#e879f9', sepia: '#c026d3' },  // 品红
];

// 按类型名 hash 取模分配
function colorForTag(tag: string, mode: 'dark' | 'sepia') {
  const i = hash(tag) % TAG_COLORS.length;
  return TAG_COLORS[i][mode];
}
```

新增类型自动获得颜色，无需修改设计系统。

## 全局 CSS 实现方案

```css
/* globals.css */
@import "tailwindcss";
@import "tw-animate-css";

@theme inline {
  --color-accent: var(--accent-base);
  --color-background: var(--surface-page);
  --color-foreground: var(--text-primary);
  --color-card: var(--surface-card);
  --color-card-foreground: var(--text-primary);
  --color-input: var(--input-bg);
  --color-border: var(--border-default);
  --color-ring: var(--focus-ring);
  /* ... 其他 Tailwind 映射 */
}

/* 基础 Token */
:root, .dark { /* ... 所有基础色板 ... */ }
.sepia { /* ... sepia 色板 ... */ }
/* 语义 Token 引用基础 Token（见前文），放在各自选择器内 */

/* focus-visible 全局 */
*:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px var(--focus-ring);
}
*:focus:not(:focus-visible) {
  outline: none;
  box-shadow: none;
}
```

- 主题切换通过 `<html data-theme="dark|sepia|system">` 控制
- `.dark` 为 fallback，`[data-theme]` 优先级更高
- `system` 模式下 JS 监听 `prefers-color-scheme`，动态切换 data-theme
- **颜色引用全部使用 `var(--token)` 形式**，不依赖 Tailwind `theme()` 函数，保证运行时切换正确

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

- 侧边栏背景 `var(--surface-sidebar)`
- 内容区背景 `var(--surface-page)`

### 2. 侧边栏

**折叠动画约束**：不使用 `transition: width`（会触发 layout reflow），改为：

```
Sidebar 容器固定宽度 (240px)
内部内容使用 transform: translateX 移入/移出
Content 区域使用 grid/flex 而非 margin-left 驱动
```

或 `width` 动画配合 `will-change` 提示，但优先方案为 `transform`。

**折叠态 (48px) 完整规范：**

| 元素 | 展开态 (240px) | 折叠态 (48px) |
|------|----------------|----------------|
| Logo | 图标 + "Novel Forge" 文字 | 仅图标，居中 |
| 导航项 | 图标 + 标签文字 | 仅图标，居中 |
| 当前页高亮 | `--nav-item-active-bg` 背景 + `--nav-item-active-text` 文字 | 同左 + 左侧 2px `--nav-item-active-indicator` 竖线 |
| Tooltip | 不显示 | hover 时显示标签文字（功能要求，实现不限） |
| 主题切换 | 下拉菜单（暗色/暖纸/跟随） | 图标按钮，点击弹出小菜单 |
| 折叠按钮 | 文字 "收起" + 图标 | 图标 "展开" |

**Tooltip 功能需求**（不限定实现方式）：
- hover 200ms delay 后出现
- 自动避让窗口边缘
- 支持长文本（截断或换行）
- 支持键盘 focus 触发
- 建议使用 Radix Tooltip 或 Floating UI 等成熟方案

### 3. 响应式布局规范

| 断点 | 宽度 | 侧边栏 | Dashboard 网格 | Writer | Chat | 移动端行为 |
|------|------|--------|----------------|--------|------|-----------|
| **Desktop** | ≥1024px | 展开 (240px) | 3 列 | 章节栏 224px + 编辑器 | 消息 + 信息侧栏 | 正常布局 |
| **Tablet** | 768–1023px | 折叠 (48px) | 2 列 | 章节栏按钮弹出 | 消息全宽 | 侧边栏自动折叠 |
| **Mobile** | <768px | Drawer (overlay) | 1 列 | 隐藏章节栏，底部按钮切换 | 消息全宽，输入框固定底部 | Drawer 代替侧边栏 |

**Dashboard 网格：** `grid-template-columns: repeat(3,1fr)` → `repeat(2,1fr)` → `1fr`
**Mobile Drawer：** 宽 280px，`transform: translateX(-100%) → translateX(0)`，带遮罩 `rgba(0,0,0,0.5)`

### 4. 工作台 (Dashboard)

- 页面标识: 紫色 label + 标题
- 导航卡片网格 (3→2→1 列)，**Solid** 卡片
- 项目列表：Solid 卡片网格、类型标签（颜色由算法从池中分配）、标题、简介、状态 Badge、更新时间、hover 删除按钮
- 空态：居中 + 图标 + 文字

### 5. 写作编辑器 (Writer)

- **背景**: `var(--editor-bg)`（`#111114` dark / `#ffffffd0` sepia）
- **内容区**: 居中 `max-width: 46rem`，padding 2rem 3rem
- **顶栏**: 左侧章节栏按钮 | 章节名 · 字数 | 搜索/AI/主题切换
- **章节结构**: 紫色竖线(2px) + 卷/部标签
- **正文**: `0.95rem` / `line-height: 1.85` / 首行缩进 `2em`
- **AI 建议**: Solid 卡片，左侧 3px 紫色边框 + `--accent-subtle` 背景
- **底栏**: 字数 · 阅读时间 | 自动保存状态
- **章节侧边栏**: 独立 224px，响应式见上表

### 6. Agent 助手 (Chat) — 信息架构

#### 消息类型

| 类型 | 视觉 | 说明 |
|------|------|------|
| `user_message` | `var(--bubble-user-bg)` 实心气泡，右对齐 | 用户文本 |
| `assistant_message` | Glass 气泡，左对齐 | AI 回复 |
| `tool_call` | 折叠卡片，可展开，`--processing-subtle` 背景 | 函数调用 |
| `tool_result` | 代码块样式，缩进 | 调用结果 |
| `reasoning` | 半透明折叠区域（见下方 Reasoning Panel） | 模型额外分析信息 |
| `system` | 居中迷你徽章 | 系统通知/错误 |
| `streaming` | 跳动紫点动画 | 流式响应占位 |

#### Reasoning Panel

用于展示**模型的额外分析信息**（不仅限于"思考链"，未来可能包含 summary、评分、纠错等）。设计不绑定特定模型行为：

- 默认折叠，显示紫色标签徽章（内容类型由 API 动态指定）
- 展开后半透明背景 (`--accent-subtle`)，斜体灰色文字
- 与主回复之间用 `--separator` 分隔
- 标签文本由 API 返回的 `label` 字段决定，UI 不做硬编码

#### 长消息折叠

- 触发条件：消息正文**超过 40 行**（基于 `\n` 计数，不受图片/代码影响）
- 折叠态：显示前 15 行 + "展开全部 (N 行)" 链接
- 代码块始终完整显示（不参与行数计数）

#### Markdown 渲染

| 元素 | 样式 |
|------|------|
| 标题 (h1-h3) | `--text-primary`，粗体，层级间距 |
| 段落 | `--text-secondary`，行高 1.75 |
| 粗体/斜体 | 标准 markdown |
| 列表 | 缩进 + 间距 0.35rem |
| 行内代码 | `--bg-elevated` 背景，`--accent-text` 文字，`--radius-sm` |
| 代码块 | 深色画布 `#0b0b0e`，等宽字体，顶栏含语言标签+复制按钮 |
| 引用块 | 左侧 3px `--accent-base` 竖线 + 斜体 |
| 链接 | `--accent-text`，hover 下划线 |

#### 输入区

- 固定底部，`--surface-page` 背景
- 圆角容器 `--radius-lg`，`--input-bg`，`--input-border`
- 左侧快捷操作图标 | 输入框 `flex:1` | 紫色发送按钮（disabled `--text-muted`）
- 可选上下文提示行（"正在基于 第3章 对话..."）

### 7. 灵感 / 文风库 / 配置 / 项目详情

- 所有页面使用 **Solid** 卡片
- 灵感列表: 3→2→1 列网格，快速录入行，琥珀色图标
- 文风库: 2→1 列网格，紫色图标，分析可滚动(max-h 6rem)
- 配置: 双列表单(sm:grid-cols-2)，mobile 单列，密码类型
- 项目详情: 返回按钮 + 标题 + 标签 + 状态 + 创建时间 + 子功能卡片网格

## 模式切换策略

| 用户选择 | 实际效果 | 实现 |
|----------|----------|------|
| `dark` | 强制暗色 | `data-theme="dark"` |
| `sepia` | 强制暖纸 | `data-theme="sepia"` |
| `system` | 系统 Dark → dark，系统 Light → sepia | 监听 `prefers-color-scheme`，切换 data-theme |

**持久化**: `localStorage: novel-forge-theme`，默认 `dark`

## 动画与过渡

```css
:root {
  --transition-fast: 150ms ease;
  --transition-normal: 250ms ease;
}

/* 卡片 hover — 微边框/阴影变化 */
.card-solid, .card-glass {
  transition: border-color var(--transition-normal),
              box-shadow var(--transition-normal);
}

/* 侧边栏折叠 — 优先使用 transform */
.sidebar-inner {
  transition: transform var(--transition-normal);
}

/* 页面切换淡入 */
main { transition: opacity 200ms ease; }

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
- 所有颜色引用使用 `var(--token)` 形式，不依赖 `theme()` 函数
- 主题切换通过 `data-theme` + CSS 变量覆盖，不依赖 Tailwind `dark:` 变体
- 所有页面覆盖 Loading / Empty / Error / Success / Processing 五种状态
- 键盘可访问性: 所有交互元素必须有可见的 `focus-visible` 环（已有全局定义）
- 侧边栏折叠动画避免 `width` transition，优先使用 `transform`
