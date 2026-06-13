# 前端现代化改版 —— 设计规格

## 概述

对 Novel Forge 前端进行全面视觉改版，从基础的 shadcn 默认灰色风格升级为 **深邃现代 (Dark-First Modern)** 设计语言，同时支持深色/暖纸双模式。

## 设计方向

| 维度 | 决策 |
|------|------|
| **风格** | 深邃现代 — 暗色优先，高对比度，大胆强调色 |
| **强调色** | 紫色 — 代表创意、想象力、神秘感 |
| **卡片风格** | 毛玻璃 (Glassmorphism) — `rgba` 半透明背景 + 微边框 |
| **侧边栏** | 可折叠 — 默认展开，写作时可折叠为图标栏 |
| **模式策略** | 暗色 + 暖纸色 (Sepia) — 无纯白模式 |

## 设计系统

### 1. 色彩系统

#### 基础色板

```css
/* Deep dark (默认) */
--bg-primary: #09090b;      /* 纯黑底 */
--bg-secondary: #0c0c0f;    /* 次级背景 */
--bg-elevated: #18181b;     /* 卡片/弹窗 */
--border-subtle: #1c1c1f;   /* 极淡边框 */
--border-default: #27272a;  /* 默认边框 */
--text-primary: #fafafa;    /* 主文字 */
--text-secondary: #d4d4d8;  /* 次级文字 */
--text-tertiary: #52525b;   /* 辅助文字 */
--text-muted: #3f3f46;      /* 禁用态 */

/* Sepia warm (浅色模式) */
--bg-primary: #f5f0eb;
--bg-elevated: rgba(255,255,255,0.6);
--border-default: #e4dcd4;
--text-primary: #2d2a24;
```

#### 强调色 (紫色)

```css
--accent-base: #7c3aed;       /* 基础紫色 */
--accent-hover: #8b5cf6;      /* Hover 紫色 */
--accent-subtle: rgba(124,58,237,0.10);  /* 极淡紫底 */
--accent-border: rgba(124,58,237,0.25);  /* 紫色边框 */
--accent-glow: rgba(124,58,237,0.15);    /* 发光 */

/* 渐变 */
--gradient-accent: linear-gradient(135deg, #7c3aed, #a855f7);
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

### 4. 全局 CSS 变更

- 已有的 `.dark` 选择器色值调整为深邃紫色调 (`--sidebar-primary` 使用紫色)
- 新增 `.sepia` 选择器作为浅色模式
- 毛玻璃效果通过 `background: rgba(255,255,255,0.03~0.05)` + `backdrop-filter: blur(8px)` 实现
- 卡片默认边框使用 `--border-subtle`，hover 时变为 `--accent-border` + `box-shadow: 0 0 16px var(--accent-glow)`

## 页面设计

### 1. 布局

```
┌─────────────────────────────────┐
│  [可折叠侧边栏]  │  Main Content │
│  240px / 48px    │              │
│  (折叠态: 图标栏)  │              │
└─────────────────────────────────┘
```

- 侧边栏宽度 240px，折叠后 48px (仅图标)
- 折叠按钮位于侧边栏底部
- 主内容区域自适应剩余宽度
- 侧边栏背景 `--bg-secondary` (#0c0c0f)

### 2. 侧边栏

- 包含: Logo + 应用名 → 分隔线 → 导航项(图标+文字) → 分隔线 → 折叠按钮/主题切换
- 导航项激活态: `--accent-subtle` 背景 + `--accent-base` 文字
- 导航项 hover: 使用毛玻璃效果
- Logo 区域使用 `--gradient-accent`

### 3. 工作台 (Dashboard)

- 页面标识徽章 (紫色 label)
- 导航卡片网格 (3列)：
  - 每个卡片包含一个图标容器 (带对应色调的背景色，如项目=紫、灵感=黄、文风=绿)
  - 标题 + 描述文字
  - 毛玻璃效果卡片，hover 紫色边框
- 项目列表：
  - 类型标签 (彩色: 科幻紫/奇幻黄/悬疑绿/...)
  - 标题 + 简介 (line-clamp-2)
  - 状态徽章 (草稿/写作中/已完成)
  - 更新时间

### 4. 写作编辑器 (Writer)

- **顶栏**: 轻量工具栏 → 折叠按钮 | 章节名 · 字数 | 搜索/AI/主题切换
- **编辑器区**: 居中对齐 (max-width: 42rem)，深色画布 (#09090b)
- **章节结构标识**: 紫色竖线 + 卷/部标签
- **正文**: 字号 0.95rem，行高 1.85，首行缩进 2em
- **AI 建议**: 左侧紫色边框 + 极淡紫底的嵌入卡片
- **底栏**: 字数统计 · 阅读时间 | 自动保存状态
- 章节侧边栏 (独立，非全局侧边栏) 保持，但使用深色风格

### 5. Agent 助手 (Chat)

- **顶栏**: 紫色渐变图标 + 标题 + 响应状态指示器 (跳动紫点动画)
- **消息区域**:
  - AI 气泡: 毛玻璃效果 (左对齐)，紫色渐变圆形头像
  - 用户气泡: 纯紫色填充 (右对齐)，灰色圆形头像
  - 流式响应: 三个紫色小点弹跳动画
- **空态**: 渐变紫色圆形 + 发光 emoji + 引导文案 + `/brainstorm` 高亮代码块
- **输入区**: 圆角容器嵌入在深色底栏中，右侧紫色发送按钮

### 6. 灵感 (Ideas)

- 快速录入行: 标题输入 + 内容输入 + 紫色添加按钮
- 卡片网格: 每张卡片带琥珀色(黄)灯泡图标
- 沿用毛玻璃卡片样式

### 7. 文风库 (Styles)

- 卡片网格 (2列):
  - 紫色调图标
  - 名称 + 来源标签
  - 文风分析 (可滚动区域, max-h 6rem)
- 导入按钮 (outline 样式)

### 8. 配置 (Config)

- 双列表单布局
- API Key 字段使用密码类型
- 保存按钮 + 成功提示 (绿色)

## 交互状态

### 加载态
- 居中的紫色旋转加载图标 (`<Loader2 className="size-6 animate-spin text-[--accent-base]" />`)
- 替代原先的 `text-zinc-400`

### 空态
- 所有列表页面统一: 居中图标 + 文字提示
- 图标使用带渐变背景的圆形容器

### 错误/边界
- 404: 保持基本布局，提供返回链接
- API 错误: 页面内以 inline error banner 形式展示，不改变整体布局

### 黑暗/暖纸模式切换
- 切换按钮位于侧边栏底部
- 支持三态: `dark` → `sepia` → `system`
- 使用 CSS 变量 + `data-theme` 属性切换

## 动画与过渡

```css
--transition-fast: 150ms ease;
--transition-normal: 250ms ease;

/* 卡片 hover */
.card {
  transition: border-color var(--transition-normal),
              box-shadow var(--transition-normal);
}
.card:hover {
  border-color: var(--accent-border);
  box-shadow: 0 0 16px var(--accent-glow);
}

/* 页面切换 */
main { transition: opacity 200ms ease; }

/* 侧边栏折叠 */
aside { transition: width var(--transition-normal); }
```

## 技术实现

- **不依赖额外 npm 包** — 全部通过 TailwindCSS v4 的 @theme 指令和 CSS 变量实现
- 修改 `globals.css` 中的颜色变量
- 新增 `.sepia` 颜色模式选择器
- 组件样式通过 TailwindCSS 的 `theme()` 函数引用设计变量
- 折叠侧边栏: `useState` + `transition` 实现
- 主题切换: Zustand store 或 `useState` + `localStorage` 持久化

## 非功能需求

- 所有页面保持 Loading/Empty/Error 三态覆盖
- 响应式: 侧边栏在窄屏自动折叠
- 键盘可访问性: 所有交互元素可 focus
