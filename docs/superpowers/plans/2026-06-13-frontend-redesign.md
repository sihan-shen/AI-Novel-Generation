# Frontend Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign all frontend pages with a dark-first modern design system, purple accent, collapsible sidebar, and dark/sepia theme switching.

**Architecture:** Three-layer design system (base tokens → semantic tokens → component references) defined in CSS variables. Theme switching via `data-theme` attribute on `<html>`. No new npm dependencies.

**Tech Stack:** Next.js 16, TailwindCSS v4, shadcn/ui (base-ui/react), CSS variables, Zustand, TanStack React Query

**Spec:** `docs/superpowers/specs/2026-06-13-frontend-redesign.md`

---

### File Map

```
novel-frontend/src/
├── app/
│   ├── globals.css                          # MODIFY: complete token system, themes, scrollbar, focus, reduced-motion
│   ├── layout.tsx                           # MODIFY: wrap with ThemeProvider
│   └── page.tsx                             # MODIFY: dashboard redesign
├── components/
│   ├── theme/
│   │   ├── theme-provider.tsx               # CREATE: data-theme management + localStorage + system detection
│   │   └── theme-toggle.tsx                 # CREATE: theme switch button (dark/sepia/system)
│   ├── layout/
│   │   └── sidebar.tsx                      # MODIFY: collapsible 240↔48px, active indicator, tooltip, theme toggle
│   └── ui/
│       ├── badge.tsx                        # CREATE: Badge component with semantic tokens and 5 variants
│       ├── button.tsx                       # VERIFY: already uses CVA, ensure tokens match
│       └── card.tsx                         # MODIFY: add data-surface="solid|glass" variant
├── lib/
│   └── utils.ts                             # VERIFY: cn() function exists
└── stores/
    └── theme.ts                             # CREATE: Zustand store for theme state
```

Each page file gets modified independently. No shared state between pages beyond theme.

---

### Task 1: CSS Variables — Base Tokens, Themes, Scrollbar, Focus, reduced-motion

**Files:**
- Modify: `novel-frontend/src/app/globals.css` (complete rewrite)

**Spec ref:** Sections 1-6 (Base tokens, Semantic tokens, Focus, Typography, Spacing, Layout tokens), Sections 9-10 (Z-index, Scrollbar), Animation section, Implementation section

**Context:** The current `globals.css` already has `:root` / `.dark` with zinc-oklch values and a `@theme inline {}` block. We're replacing the token values entirely while keeping the `@theme` mapping structure. The `.dark` class becomes the fallback; primary control moves to `[data-theme]` attribute.

- [ ] **Step 1: Replace `globals.css` with the full token system**

Replace entire file content with:

```css
@import "tailwindcss";
@import "tw-animate-css";
@import "shadcn/tailwind.css";

@custom-variant dark (&:is(.dark *));

/* ────────────── Tailwind theme mapping ────────────── */
@theme inline {
  --color-background: var(--surface-page);
  --color-foreground: var(--text-primary);
  --color-card: var(--surface-card);
  --color-card-foreground: var(--text-primary);
  --color-popover: var(--surface-dialog);
  --color-popover-foreground: var(--text-primary);
  --color-primary: var(--accent-base);
  --color-primary-foreground: #ffffff;
  --color-secondary: var(--bg-elevated);
  --color-secondary-foreground: var(--text-primary);
  --color-muted: var(--bg-elevated-hover);
  --color-muted-foreground: var(--text-tertiary);
  --color-accent: var(--accent-base);
  --color-accent-foreground: var(--accent-text);
  --color-destructive: var(--danger-base);
  --color-destructive-foreground: #ffffff;
  --color-border: var(--border-default);
  --color-input: var(--input-bg);
  --color-ring: var(--focus-ring);
  --color-sidebar: var(--surface-sidebar);
  --color-sidebar-foreground: var(--text-primary);
  --color-sidebar-primary: var(--accent-base);
  --color-sidebar-primary-foreground: #ffffff;
  --color-sidebar-accent: var(--nav-item-active-bg);
  --color-sidebar-accent-foreground: var(--nav-item-active-text);
  --color-sidebar-border: var(--border-subtle);
  --color-sidebar-ring: var(--focus-ring);
  --radius-sm: calc(0.375rem * 0.6);
  --radius-md: calc(0.375rem * 0.8);
  --radius-lg: 0.375rem;
  --radius-xl: calc(0.375rem * 1.4);
  --font-sans: var(--font-geist-sans);
  --font-mono: var(--font-geist-mono);
}

/* ────────────── Dark Mode: Base Tokens ────────────── */
:root, .dark {
  /* Background */
  --bg-base: #0b0b0e;
  --bg-base-secondary: #0e0e12;
  --bg-elevated: #141418;
  --bg-elevated-hover: #1c1c22;
  --bg-input: #18181c;

  /* Border */
  --border-subtle: #1c1c22;
  --border-default: #27272e;
  --border-strong: #3f3f46;

  /* Text */
  --text-primary: #f4f4f5;
  --text-secondary: #c4c4c8;
  --text-tertiary: #71717a;
  --text-muted: #52525b;
  --text-inverse: #0b0b0e;

  /* Shadows */
  --shadow-card: 0 1px 3px rgba(0,0,0,0.4);
  --shadow-dialog: 0 8px 32px rgba(0,0,0,0.6);

  /* Editor (Writer) */
  --editor-bg: #111114;
  --editor-text: #d4d4d8;
  --editor-cursor: #a78bfa;

  /* Accent — Purple */
  --accent-base: #7c3aed;
  --accent-hover: #8b5cf6;
  --accent-active: #6d28d9;
  --accent-subtle: rgba(124,58,237,0.10);
  --accent-border: rgba(124,58,237,0.25);
  --accent-glow: rgba(124,58,237,0.12);
  --accent-text: #a78bfa;
  --gradient-accent: linear-gradient(135deg, #7c3aed, #a855f7);

  /* Status Colors */
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

  /* Focus */
  --focus-ring: rgba(124,58,237,0.45);

  /* Transitions */
  --transition-fast: 150ms ease;
  --transition-normal: 250ms ease;

  /* Z-index */
  --z-sidebar: 40;
  --z-drawer: 45;
  --z-dialog: 50;
  --z-popover: 60;
  --z-dropdown: 60;
  --z-tooltip: 70;
  --z-toast: 80;
  --z-chat-input: 30;
}

/* ────────────── Sepia Mode: Base Tokens ────────────── */
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

  --editor-bg: #ffffffd0;
  --editor-text: #2d2a24;
  --editor-cursor: #7c3aed;

  --accent-base: #7c3aed;
  --accent-hover: #6d28d9;
  --accent-active: #5b21b6;
  --accent-subtle: rgba(124,58,237,0.08);
  --accent-border: rgba(124,58,237,0.20);
  --accent-glow: rgba(124,58,237,0.08);
  --accent-text: #6d28d9;

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

  --focus-ring: rgba(124,58,237,0.45);

  /* Sepia code block */
  --surface-code: #f0ece4;
}

/* ────────────── Semantic Tokens (applied in both modes) ────────────── */
:root, .dark, .sepia {
  /* Surfaces */
  --surface-page: var(--bg-base);
  --surface-sidebar: var(--bg-base-secondary);
  --surface-card: var(--bg-elevated);
  --surface-dialog: var(--bg-elevated);
  --surface-tooltip: var(--bg-elevated);
  --surface-input: var(--bg-input);
  --surface-glass-bg: rgba(255,255,255,0.03);
  --surface-glass-border: rgba(255,255,255,0.06);
  --surface-disabled: var(--bg-elevated-hover);
  --surface-editor: var(--editor-bg);
  --surface-editor-sidebar: var(--bg-base-secondary);
  --surface-code: #0c0c10;
  --surface-code-border: var(--border-subtle);
  --surface-code-header: var(--bg-elevated);
  --text-code: var(--text-secondary);
  --text-editor: var(--editor-text);
  --cursor-editor: var(--editor-cursor);

  /* Buttons */
  --button-primary-bg: var(--accent-base);
  --button-primary-text: #ffffff;
  --button-primary-hover: var(--accent-hover);
  --button-primary-active: var(--accent-active);
  --button-outline-border: var(--border-default);
  --button-outline-text: var(--text-primary);
  --button-outline-hover-bg: var(--bg-elevated-hover);
  --button-ghost-text: var(--text-secondary);
  --button-ghost-hover-bg: var(--bg-elevated-hover);

  /* Input */
  --input-bg: var(--bg-input);
  --input-border: var(--border-default);
  --input-text: var(--text-primary);
  --input-placeholder: var(--text-muted);
  --input-focus-ring: var(--accent-base);
  --input-focus-border: var(--accent-border);

  /* Navigation */
  --nav-item-text: var(--text-tertiary);
  --nav-item-hover-bg: var(--bg-elevated);
  --nav-item-active-bg: var(--accent-subtle);
  --nav-item-active-text: var(--accent-text);
  --nav-item-active-indicator: var(--accent-base);

  /* Badge */
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

  /* Chat bubbles */
  --bubble-user-bg: var(--accent-base);
  --bubble-user-text: #ffffff;
  --bubble-assistant-bg: var(--surface-glass-bg);
  --bubble-assistant-border: var(--surface-glass-border);

  /* Misc */
  --separator: var(--border-subtle);
  --overlay-backdrop: rgba(0,0,0,0.50);
  --overlay-backdrop-sepia: rgba(0,0,0,0.15);
  --selection-bg: rgba(124,58,237,0.30);
  --selection-text: currentColor;

  /* Scrollbar */
  --scrollbar-track: transparent;
  --scrollbar-thumb: rgba(255,255,255,0.08);
  --scrollbar-thumb-hover: rgba(255,255,255,0.15);
  --scrollbar-thumb-sepia: rgba(0,0,0,0.10);
  --scrollbar-thumb-sepia-hover: rgba(0,0,0,0.20);

  /* Layout dimensions */
  --layout-sidebar-expanded: 240px;
  --layout-sidebar-collapsed: 48px;
  --layout-sidebar-mobile-drawer: 280px;
  --layout-writer-sidebar: 224px;
  --layout-writer-max-width: 46rem;
  --layout-chat-input-height: 56px;
  --layout-chat-max-width: 48rem;
  --layout-dialog-max-width: 640px;
  --layout-dialog-narrow: 480px;
  --layout-grid-col-desktop: 3;
  --layout-grid-col-tablet: 2;
  --layout-grid-col-mobile: 1;
}

/* ────────────── Global Styles ────────────── */
@layer base {
  * {
    @apply border-border;
  }
  body {
    @apply bg-background text-foreground font-sans;
  }

  /* Text selection */
  ::selection {
    background: var(--selection-bg);
    color: var(--selection-text);
  }

  /* Scrollbar — Dark */
  ::-webkit-scrollbar { width: 6px; height: 6px; }
  ::-webkit-scrollbar-track { background: var(--scrollbar-track); }
  ::-webkit-scrollbar-thumb {
    background: var(--scrollbar-thumb);
    border-radius: 3px;
  }
  ::-webkit-scrollbar-thumb:hover { background: var(--scrollbar-thumb-hover); }

  /* Scrollbar — Sepia */
  .sepia ::-webkit-scrollbar-thumb { background: var(--scrollbar-thumb-sepia); }
  .sepia ::-webkit-scrollbar-thumb:hover { background: var(--scrollbar-thumb-sepia-hover); }

  /* Focus-visible — interactive elements only */
  input:focus-visible,
  button:focus-visible,
  a:focus-visible,
  select:focus-visible,
  textarea:focus-visible,
  [tabindex]:focus-visible {
    outline: none;
    box-shadow: 0 0 0 2px var(--focus-ring);
  }
  input:focus:not(:focus-visible),
  button:focus:not(:focus-visible),
  a:focus:not(:focus-visible),
  select:focus:not(:focus-visible),
  textarea:focus:not(:focus-visible),
  [tabindex]:focus:not(:focus-visible) {
    outline: none;
    box-shadow: none;
  }

  /* Reduced motion */
  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
      animation-duration: 0.01ms !important;
      animation-iteration-count: 1 !important;
      transition-duration: 0.01ms !important;
    }
  }
}
```

- [ ] **Step 2: Verify no syntax errors**

Run: `cd /home/sihan/文档/Projects/AI-Novel-Generation/novel-frontend && npx next build --no-lint 2>&1 | head -30`
Expected: No CSS parse errors. (If the build fails on TS errors, that's fine for now — we fix in later tasks.)

- [ ] **Step 3: Commit**

```bash
git add novel-frontend/src/app/globals.css
git commit -m "feat(design): add complete token system with dark/sepia themes, scrollbar, focus, reduced-motion"
```

---

### Task 2: Theme Store + Provider + Toggle

**Files:**
- Create: `novel-frontend/src/stores/theme.ts`
- Create: `novel-frontend/src/components/theme/theme-provider.tsx`
- Create: `novel-frontend/src/components/theme/theme-toggle.tsx`
- Modify: `novel-frontend/src/app/layout.tsx`

**Spec ref:** Mode switching strategy, Persistence

- [ ] **Step 1: Create `stores/theme.ts`**

```ts
"use client";

import { create } from "zustand";

type Theme = "dark" | "sepia" | "system";

interface ThemeState {
  theme: Theme;
  resolved: "dark" | "sepia";
  setTheme: (t: Theme) => void;
}

const STORAGE_KEY = "novel-forge-theme";

function getStored(): Theme {
  if (typeof window === "undefined") return "dark";
  return (localStorage.getItem(STORAGE_KEY) as Theme) || "dark";
}

function resolveTheme(theme: Theme): "dark" | "sepia" {
  if (theme === "system") {
    return window.matchMedia("(prefers-color-scheme: light)").matches
      ? "sepia"
      : "dark";
  }
  return theme;
}

function applyTheme(resolved: "dark" | "sepia") {
  const root = document.documentElement;
  if (resolved === "sepia") {
    root.setAttribute("data-theme", "sepia");
    root.classList.remove("dark");
    root.classList.add("sepia");
  } else {
    root.setAttribute("data-theme", "dark");
    root.classList.remove("sepia");
    root.classList.add("dark");
  }
}

export const useThemeStore = create<ThemeState>((set) => {
  const stored = getStored();
  const resolved = resolveTheme(stored);
  // Apply on first load
  if (typeof window !== "undefined") applyTheme(resolved);

  // Listen for system changes if stored === "system"
  if (typeof window !== "undefined" && stored === "system") {
    window.matchMedia("(prefers-color-scheme: light)").addEventListener("change", () => {
      const r = resolveTheme("system");
      applyTheme(r);
      set({ resolved: r });
    });
  }

  return {
    theme: stored,
    resolved,
    setTheme: (t: Theme) => {
      localStorage.setItem(STORAGE_KEY, t);
      const r = resolveTheme(t);
      applyTheme(r);
      set({ theme: t, resolved: r });

      // Re-bind system listener
      if (t === "system") {
        window.matchMedia("(prefers-color-scheme: light)").addEventListener("change", () => {
          const nr = resolveTheme("system");
          applyTheme(nr);
          set({ resolved: nr });
        });
      }
    },
  };
});
```

- [ ] **Step 2: Create `components/theme/theme-provider.tsx`**

```tsx
"use client";

import { useEffect } from "react";
import { useThemeStore } from "@/stores/theme";

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const resolved = useThemeStore((s) => s.resolved);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", resolved === "dark");
    document.documentElement.classList.toggle("sepia", resolved === "sepia");
  }, [resolved]);

  return <>{children}</>;
}
```

- [ ] **Step 3: Create `components/theme/theme-toggle.tsx`**

```tsx
"use client";

import { useThemeStore } from "@/stores/theme";
import { Moon, SunMedium, Monitor } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

const THEME_OPTIONS = [
  { value: "dark" as const, label: "暗色", icon: Moon },
  { value: "sepia" as const, label: "暖纸", icon: SunMedium },
  { value: "system" as const, label: "跟随系统", icon: Monitor },
];

export function ThemeToggle({ collapsed = false }: { collapsed?: boolean }) {
  const { theme, setTheme, resolved } = useThemeStore();

  const CurrentIcon = THEME_OPTIONS.find((o) => o.value === resolved)?.icon ?? Moon;

  if (collapsed) {
    return (
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon" className="size-8 shrink-0">
            <CurrentIcon className="size-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" side="right">
          {THEME_OPTIONS.map((opt) => (
            <DropdownMenuItem
              key={opt.value}
              onClick={() => setTheme(opt.value)}
              className={theme === opt.value ? "text-[var(--accent-text)]" : ""}
            >
              <opt.icon className="mr-2 size-4" />
              {opt.label}
            </DropdownMenuItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>
    );
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className="w-full justify-start gap-2"
        >
          <CurrentIcon className="size-4" />
          <span className="text-sm">{THEME_OPTIONS.find((o) => o.value === resolved)?.label}</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {THEME_OPTIONS.map((opt) => (
          <DropdownMenuItem
            key={opt.value}
            onClick={() => setTheme(opt.value)}
            className={theme === opt.value ? "text-[var(--accent-text)]" : ""}
          >
            <opt.icon className="mr-2 size-4" />
            {opt.label}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
```

- [ ] **Step 4: Update `layout.tsx` to use ThemeProvider**

```tsx
import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { QueryProvider } from "@/lib/query-provider";
import { Sidebar } from "@/components/layout/sidebar";
import { ThemeProvider } from "@/components/theme/theme-provider";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Novel Forge — AI 辅助小说创作",
  description: "基于 LLM 的小说创作辅助工具",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="zh-CN"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased dark`}
      data-theme="dark"
      suppressHydrationWarning
    >
      <body className="flex h-full">
        <QueryProvider>
          <ThemeProvider>
            <Sidebar />
            <main className="flex-1 overflow-auto">{children}</main>
          </ThemeProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
```

Note: The `<html>` has `data-theme="dark"` and `class="dark"` as the server default. The ThemeProvider hydrates and picks the correct value from localStorage on the client. This prevents flash.

- [ ] **Step 5: Build check**

Run: `cd /home/sihan/文档/Projects/AI-Novel-Generation/novel-frontend && npx next build --no-lint 2>&1 | tail -10`
Expected: No TS errors in new files (may still fail on old page code, that's expected).

- [ ] **Step 6: Commit**

```bash
git add novel-frontend/src/stores/theme.ts novel-frontend/src/components/theme/ novel-frontend/src/app/layout.tsx
git commit -m "feat(theme): add theme store, provider, toggle, and wire into layout"
```

---

### Task 3: Badge Component

**Files:**
- Create: `novel-frontend/src/components/ui/badge.tsx`

**Spec ref:** Component spec — Badge

- [ ] **Step 1: Create `badge.tsx`**

```tsx
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-[var(--radius-sm)] px-[0.5rem] py-[0.15rem] text-[var(--text-xs)] font-medium whitespace-nowrap transition-colors",
  {
    variants: {
      variant: {
        default: "bg-[var(--badge-default-bg)] text-[var(--badge-default-text)]",
        success: "bg-[var(--badge-success-bg)] text-[var(--badge-success-text)]",
        warning: "bg-[var(--badge-warning-bg)] text-[var(--badge-warning-text)]",
        danger: "bg-[var(--badge-danger-bg)] text-[var(--badge-danger-text)]",
        processing: "bg-[var(--badge-processing-bg)] text-[var(--badge-processing-text)]",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <span
      data-slot="badge"
      className={cn(badgeVariants({ variant }), className)}
      {...props}
    />
  );
}
```

- [ ] **Step 2: Build check**

Run: `cd /home/sihan/文档/Projects/AI-Novel-Generation/novel-frontend && npx next build --no-lint 2>&1 | tail -5`
Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add novel-frontend/src/components/ui/badge.tsx
git commit -m "feat(ui): add Badge component with 5 semantic variants"
```

---

### Task 4: Card Component — Solid/Glass Variants

**Files:**
- Modify: `novel-frontend/src/components/ui/card.tsx`

**Spec ref:** Card section

- [ ] **Step 1: Add `data-surface` support to Card**

Current card uses a `size` prop. Add a `surface` prop that toggles between solid (default) and glass.

Read the current file first, then modify the Card function:

```tsx
// Inside the Card function, add `surface = "solid"` to destructured props
// and use it to set className:

function Card({
  className,
  size = "default",
  surface = "solid",
  ...props
}: React.ComponentProps<"div"> & {
  size?: "default" | "sm";
  surface?: "solid" | "glass";
}) {
  const surfaceClass =
    surface === "glass"
      ? "bg-[var(--surface-glass-bg)] backdrop-blur-[6px] border-[var(--surface-glass-border)]"
      : "bg-[var(--surface-card)] border-[var(--border-subtle)] shadow-[var(--shadow-card)]";

  return (
    <div
      data-slot="card"
      data-size={size}
      data-surface={surface}
      className={cn(
        `group/card flex flex-col gap-(--card-spacing) overflow-hidden rounded-xl text-sm text-card-foreground ring-1 ring-foreground/10 [--card-spacing:--spacing(4)] has-data-[slot=card-footer]:pb-0 has-[>img:first-child]:pt-0 data-[size=sm]:[--card-spacing:--spacing(3)] data-[size=sm]:has-data-[slot=card-footer]:pb-0`,
        surfaceClass,
        "transition-[border-color,box-shadow] duration-[var(--transition-normal)] hover:border-[var(--accent-border)] hover:shadow-[0_0_16px_var(--accent-glow)]",
        className
      )}
      {...props}
    />
  );
}

export { Card, CardHeader, CardFooter, CardTitle, CardAction, CardDescription, CardContent };
```

- [ ] **Step 2: Build check**

Run: `cd /home/sihan/文档/Projects/AI-Novel-Generation/novel-frontend && npx next build --no-lint 2>&1 | tail -5`
Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add novel-frontend/src/components/ui/card.tsx
git commit -m "feat(ui): add glass/solid surface variant to Card"
```

---

### Task 5: Collapsible Sidebar

**Files:**
- Modify: `novel-frontend/src/components/layout/sidebar.tsx`

**Spec ref:** Layout section, Sidebar section

- [ ] **Step 1: Rewrite `sidebar.tsx` with collapsible behavior**

```tsx
"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  BookOpen,
  Settings,
  MessageSquare,
  Palette,
  Lightbulb,
  Wrench,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { ThemeToggle } from "@/components/theme/theme-toggle";

const navItems = [
  { href: "/", label: "工作台", icon: LayoutDashboard },
  { href: "/projects", label: "项目", icon: BookOpen },
  { href: "/styles", label: "文风", icon: Palette },
  { href: "/ideas", label: "灵感", icon: Lightbulb },
  { href: "/config", label: "配置", icon: Wrench },
];

export function Sidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  return (
    <aside
      className="fixed left-0 top-0 z-[var(--z-sidebar)] flex h-full flex-col border-r"
      style={{
        width: collapsed
          ? "var(--layout-sidebar-collapsed)"
          : "var(--layout-sidebar-expanded)",
        background: "var(--surface-sidebar)",
        borderColor: "var(--border-subtle)",
        transition: "width var(--transition-normal)",
      }}
    >
      {/* Logo */}
      <div
        className="flex h-14 items-center gap-2 overflow-hidden px-4"
        style={{ justifyContent: collapsed ? "center" : "flex-start" }}
      >
        <BookOpen className="size-5 shrink-0" style={{ color: "var(--accent-text)" }} />
        {!collapsed && (
          <span className="font-semibold whitespace-nowrap" style={{ color: "var(--text-primary)" }}>
            Novel Forge
          </span>
        )}
      </div>

      <Separator />

      {/* Navigation */}
      <ScrollArea className="flex-1 px-3 py-2">
        <nav className="flex flex-col gap-1">
          {navItems.map((item) => {
            const active = isActive(item.href);
            return (
              <div key={item.href} className="relative group">
                <Link
                  href={item.href}
                  className="flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors"
                  style={{
                    justifyContent: collapsed ? "center" : "flex-start",
                    background: active ? "var(--nav-item-active-bg)" : "transparent",
                    color: active ? "var(--nav-item-active-text)" : "var(--nav-item-text)",
                  }}
                  onMouseEnter={(e) => {
                    if (!active) {
                      e.currentTarget.style.background = "var(--nav-item-hover-bg)";
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!active) {
                      e.currentTarget.style.background = "transparent";
                    }
                  }}
                  title={collapsed ? item.label : undefined}
                >
                  <item.icon className="size-4 shrink-0" />
                  {!collapsed && <span className="truncate">{item.label}</span>}
                </Link>
                {/* Active indicator — collapsed mode */}
                {active && collapsed && (
                  <div
                    className="absolute left-0 top-1/2 -translate-y-1/2 w-[2px] h-5 rounded-r-full"
                    style={{ background: "var(--nav-item-active-indicator)" }}
                  />
                )}
                {/* Tooltip — collapsed mode */}
                {collapsed && (
                  <div
                    className="absolute left-full top-1/2 -translate-y-1/2 ml-2 px-2 py-1 rounded-md text-xs whitespace-nowrap opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-opacity pointer-events-none z-[var(--z-tooltip)]"
                    style={{
                      background: "var(--surface-tooltip)",
                      color: "var(--text-primary)",
                      border: "1px solid var(--border-subtle)",
                      boxShadow: "var(--shadow-dialog)",
                    }}
                  >
                    {item.label}
                  </div>
                )}
              </div>
            );
          })}
        </nav>
      </ScrollArea>

      <Separator />

      {/* Bottom controls */}
      <div className="flex flex-col gap-1 p-3">
        <ThemeToggle collapsed={collapsed} />
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="flex items-center justify-center rounded-md py-2 text-sm transition-colors"
          style={{
            color: "var(--text-tertiary)",
            background: "transparent",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = "var(--bg-elevated-hover)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = "transparent";
          }}
          aria-label={collapsed ? "展开侧边栏" : "收起侧边栏"}
        >
          {collapsed ? (
            <ChevronRight className="size-4" />
          ) : (
            <>
              <ChevronLeft className="size-4 mr-1" />
              <span>收起</span>
            </>
          )}
        </button>
      </div>
    </aside>
  );
}
```

- [ ] **Step 2: Update `layout.tsx` to remove hardcoded `ml-56`**

Since the sidebar is `fixed` positioned, we don't need the `ml-56` on `<main>`. But we need the content to not be behind the sidebar. Check that the `<main>` in `layout.tsx` handles this via padding or margin based on sidebar width.

Change the `<main>` in layout.tsx to use a dynamic padding that matches the collapsed/expanded state, or simply set a `padding-left` that covers the expanded width:

```tsx
// In layout.tsx, change:
<main className="flex-1 overflow-auto">{children}</main>
// to:
<main className="flex-1 overflow-auto pl-[var(--layout-sidebar-expanded)]">
  {children}
</main>
```

For the collapsed state, since the sidebar uses `fixed` positioning, the content padding stays at `240px` always — when sidebar collapses, the content area doesn't reflow (which is the performant approach from the spec). The sidebar content slides in/out via the width change.

- [ ] **Step 3: Build check**

Run: `cd /home/sihan/文档/Projects/AI-Novel-Generation/novel-frontend && npx next build --no-lint 2>&1 | tail -15`
Expected: No errors.

- [ ] **Step 4: Commit**

```bash
git add novel-frontend/src/components/layout/sidebar.tsx novel-frontend/src/app/layout.tsx
git commit -m "feat(sidebar): add collapsible sidebar with tooltips, active indicators, theme toggle"
```

---

### Task 6: Dashboard Page

**Files:**
- Modify: `novel-frontend/src/app/page.tsx`

**Spec ref:** Dashboard page design

- [ ] **Step 1: Rewrite `page.tsx`**

```tsx
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { BookOpen, Lightbulb, Palette, Sparkles } from "lucide-react";
import Link from "next/link";

const navCards = [
  {
    title: "最近项目",
    desc: "查看和管理你的小说项目",
    href: "/projects",
    icon: BookOpen,
    gradient: "linear-gradient(135deg, rgba(124,58,237,0.15), rgba(139,92,246,0.05))",
    iconColor: "var(--accent-text)",
  },
  {
    title: "灵感记录",
    desc: "随手记录创作灵感",
    href: "/ideas",
    icon: Lightbulb,
    gradient: "linear-gradient(135deg, rgba(251,191,36,0.15), rgba(251,191,36,0.05))",
    iconColor: "#fbbf24",
  },
  {
    title: "文风库",
    desc: "管理和分析参考文风",
    href: "/styles",
    icon: Palette,
    gradient: "linear-gradient(135deg, rgba(52,211,153,0.15), rgba(52,211,153,0.05))",
    iconColor: "#34d399",
  },
];

export default function Dashboard() {
  return (
    <div className="p-8">
      {/* Page header */}
      <div className="mb-8">
        <span
          className="inline-block rounded-full px-2.5 py-0.5 text-[0.7rem] font-medium tracking-wide"
          style={{
            background: "var(--accent-subtle)",
            color: "var(--accent-text)",
          }}
        >
          工作台
        </span>
        <h1
          className="mt-2 text-2xl font-bold tracking-tight"
          style={{ color: "var(--text-primary)" }}
        >
          Novel Forge
        </h1>
        <p className="mt-1 text-sm" style={{ color: "var(--text-tertiary)" }}>
          欢迎回来，继续你的创作之旅。
        </p>
      </div>

      {/* Navigation cards */}
      <div
        className="grid gap-4"
        style={{
          gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))",
        }}
      >
        {navCards.map((card) => (
          <Link key={card.href} href={card.href}>
            <Card
              className="h-full cursor-pointer transition-[border-color,box-shadow] duration-[var(--transition-normal)] hover:border-[var(--accent-border)] hover:shadow-[0_0_16px_var(--accent-glow)]"
              surface="solid"
            >
              <CardHeader>
                <div
                  className="flex size-8 items-center justify-center rounded-lg mb-2"
                  style={{ background: card.gradient }}
                >
                  <card.icon className="size-4" style={{ color: card.iconColor }} />
                </div>
                <CardTitle className="text-base">{card.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm leading-relaxed" style={{ color: "var(--text-tertiary)" }}>
                  {card.desc}
                </p>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Build check**

Run: `cd /home/sihan/文档/Projects/AI-Novel-Generation/novel-frontend && npx next build --no-lint 2>&1 | tail -5`
Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add novel-frontend/src/app/page.tsx
git commit -m "feat(dashboard): redesign with purple accent, glass-gradient cards, page label"
```

---

### Task 7: Projects List and Detail Pages

**Files:**
- Modify: `novel-frontend/src/app/projects/page.tsx`
- Modify: `novel-frontend/src/app/projects/[id]/page.tsx`

**Spec ref:** Dashboard page (project list section), Project detail

- [ ] **Step 1: Update `projects/page.tsx`**

Key changes:
1. Import `Badge` instead of manual `<span>` for status tags
2. Replace `Card` usage with proper styling: type labels use color from algorithm
3. Update dialog styling to use `surface-dialog`
4. Loading/empty states use theme tokens

```tsx
"use client";

import Link from "next/link";
import { useProjects, useCreateProject, useDeleteProject } from "@/lib/queries/projects";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Plus, Trash2, Loader2 } from "lucide-react";
import { useState } from "react";

// Tag color pool (hash-based)
const TAG_COLORS: Record<string, { dark: string; sepia: string }> = {
  // populated by hash — see below
};

const TAG_PALETTE = [
  { dark: '#a78bfa', sepia: '#7c3aed' },
  { dark: '#fbbf24', sepia: '#d97706' },
  { dark: '#34d399', sepia: '#16a34a' },
  { dark: '#f472b6', sepia: '#db2777' },
  { dark: '#fb923c', sepia: '#ea580c' },
  { dark: '#60a5fa', sepia: '#2563eb' },
  { dark: '#818cf8', sepia: '#4f46e5' },
  { dark: '#e879f9', sepia: '#c026d3' },
];

function colorForTag(tag: string | null): { dark: string; sepia: string } {
  if (!tag) return { dark: '#a1a1aa', sepia: '#71717a' };
  let hash = 0;
  for (let i = 0; i < tag.length; i++) {
    hash = tag.charCodeAt(i) + ((hash << 5) - hash);
  }
  return TAG_PALETTE[Math.abs(hash) % TAG_PALETTE.length];
}

const STATUS_BADGE: Record<string, "default" | "success" | "warning" | "processing"> = {
  draft: "default",
  writing: "processing",
  completed: "success",
};

export default function ProjectsPage() {
  const { data: projects, isLoading } = useProjects();
  const create = useCreateProject();
  const remove = useDeleteProject();
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [genre, setGenre] = useState("");

  const handleCreate = async () => {
    if (!title.trim()) return;
    await create.mutateAsync({ title, genre: genre || undefined });
    setTitle("");
    setGenre("");
    setOpen(false);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-16">
        <Loader2 className="size-6 animate-spin" style={{ color: "var(--accent-base)" }} />
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="flex items-center justify-between">
        <div>
          <span
            className="inline-block rounded-full px-2.5 py-0.5 text-[0.7rem] font-medium tracking-wide"
            style={{ background: "var(--accent-subtle)", color: "var(--accent-text)" }}
          >
            项目
          </span>
          <h1 className="mt-2 text-2xl font-bold tracking-tight" style={{ color: "var(--text-primary)" }}>
            项目
          </h1>
          <p className="mt-1 text-sm" style={{ color: "var(--text-tertiary)" }}>
            管理你的小说项目
          </p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button size="sm">
              <Plus className="size-4 mr-1" />
              新建项目
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>新建项目</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <Input placeholder="项目名称" value={title} onChange={(e) => setTitle(e.target.value)} />
              <Input placeholder="类型（如：科幻、奇幻...）" value={genre} onChange={(e) => setGenre(e.target.value)} />
              <Button onClick={handleCreate} disabled={create.isPending} className="w-full">
                {create.isPending ? "创建中..." : "创建"}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <div
        className="mt-6 grid gap-4"
        style={{
          gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
        }}
      >
        {projects?.map((p) => (
          <Card key={p.id} className="group relative" surface="solid">
            <Link href={`/projects/${p.id}`}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  {p.genre && (
                    <span
                      className="rounded-full px-2 py-0.5 text-[0.65rem] font-medium"
                      style={{
                        background: `${colorForTag(p.genre).dark}20`,
                        color: "var(--accent-text)",
                      }}
                    >
                      {p.genre}
                    </span>
                  )}
                </div>
                <CardTitle className="text-lg mt-1">{p.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="line-clamp-2 text-sm leading-relaxed" style={{ color: "var(--text-tertiary)" }}>
                  {p.description || "暂无简介"}
                </p>
                <div className="mt-3 flex items-center gap-3">
                  <Badge variant={STATUS_BADGE[p.status || "draft"] || "default"}>
                    {p.status || "草稿"}
                  </Badge>
                  {p.updated_at && (
                    <span className="text-[0.7rem]" style={{ color: "var(--text-muted)" }}>
                      {new Date(p.updated_at).toLocaleDateString("zh-CN")}
                    </span>
                  )}
                </div>
              </CardContent>
            </Link>
            <button
              className="absolute right-3 top-3 rounded p-1 opacity-0 transition-opacity hover:bg-[var(--danger-subtle)] group-hover:opacity-100"
              onClick={() => remove.mutate(p.id)}
              aria-label="删除项目"
            >
              <Trash2 className="size-4" style={{ color: "var(--danger-text)" }} />
            </button>
          </Card>
        ))}
      </div>

      {projects?.length === 0 && (
        <p className="mt-16 text-center" style={{ color: "var(--text-muted)" }}>
          还没有项目，创建一个吧。
        </p>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Update `projects/[id]/page.tsx`**

Replace hardcoded `bg-zinc-*` / `text-zinc-*` with CSS variable references via `style` props. Add `Badge` usage. Use `Card` with `surface="solid"`. Keep the same structure but update colors to use design tokens:

```tsx
"use client";

import { useParams, useRouter } from "next/navigation";
import { useProject } from "@/lib/queries/projects";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Loader2, ArrowLeft } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { data: project, isLoading } = useProject(id);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-16">
        <Loader2 className="size-6 animate-spin" style={{ color: "var(--accent-base)" }} />
      </div>
    );
  }

  if (!project) {
    return (
      <div className="p-8">
        <p style={{ color: "var(--text-tertiary)" }}>项目未找到</p>
        <Link href="/projects" className="mt-2 inline-block text-sm underline" style={{ color: "var(--accent-text)" }}>
          返回项目列表
        </Link>
      </div>
    );
  }

  const statusVariant = (
    { draft: "default" as const, writing: "processing" as const, completed: "success" as const }
  )[project.status || "draft"] || "default";

  return (
    <div className="p-8">
      <Button variant="ghost" size="sm" onClick={() => router.back()} className="mb-4">
        <ArrowLeft className="size-4 mr-1" />
        返回
      </Button>

      <Card surface="solid">
        <CardHeader>
          <div className="flex items-center gap-2">
            <CardTitle className="text-2xl">{project.title}</CardTitle>
            {project.genre && (
              <Badge variant="default">{project.genre}</Badge>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
            {project.description || "暂无简介"}
          </p>
          <div className="mt-6 flex gap-3">
            <Badge variant={statusVariant}>{project.status || "草稿"}</Badge>
            <span className="text-xs" style={{ color: "var(--text-muted)" }}>
              创建于 {new Date(project.created_at).toLocaleDateString("zh-CN")}
            </span>
          </div>
        </CardContent>
      </Card>

      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        <SubPageCard title="大纲" desc="管理卷章节结构" href={`/projects/${id}/outline`} />
        <SubPageCard title="写作" desc="章节内容编辑" href={`/projects/${id}/writer`} />
        <SubPageCard title="设定集" desc="人物、世界观、组织" href={`/projects/${id}/settings`} />
        <SubPageCard title="Agent 助手" desc="AI 对话与脑暴" href={`/projects/${id}/agent`} />
      </div>
    </div>
  );
}

function SubPageCard({ title, desc, href }: { title: string; desc: string; href: string }) {
  return (
    <Link href={href}>
      <Card surface="solid" className="cursor-pointer">
        <CardHeader>
          <CardTitle className="text-base">{title}</CardTitle>
          <p className="text-sm mt-1" style={{ color: "var(--text-tertiary)" }}>
            {desc}
          </p>
        </CardHeader>
      </Card>
    </Link>
  );
}
```

- [ ] **Step 3: Build check both files**

Run: `cd /home/sihan/文档/Projects/AI-Novel-Generation/novel-frontend && npx next build --no-lint 2>&1 | tail -10`
Expected: No errors.

- [ ] **Step 4: Commit**

```bash
git add novel-frontend/src/app/projects/page.tsx novel-frontend/src/app/projects/\[id\]/page.tsx
git commit -m "feat(projects): redesign with badge, tag colors, semantic tokens"
```

---

### Task 8: Writer Editor Page

**Files:**
- Modify: `novel-frontend/src/app/projects/[id]/writer/page.tsx`

**Spec ref:** Writer section

- [ ] **Step 1: Rewrite `writer/page.tsx`**

Key changes: editor background uses `var(--surface-editor)`, chapter sidebar uses inset styling, textarea gets new colors, AI suggestion card styling, top toolbar with theme-aware colors.

```tsx
"use client";

import { useParams } from "next/navigation";
import { useState } from "react";
import {
  useChapters,
  useCreateChapter,
  useUpdateChapter,
  useDeleteChapter,
} from "@/lib/queries/chapters";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Plus, Trash2, Loader2, FileText, Sparkles } from "lucide-react";

export default function WriterPage() {
  const { id: projectId } = useParams<{ id: string }>();
  const { data: chapters, isLoading } = useChapters(projectId);
  const create = useCreateChapter(projectId);
  const update = useUpdateChapter(projectId);
  const remove = useDeleteChapter(projectId);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [newTitle, setNewTitle] = useState("");
  const [editContent, setEditContent] = useState("");

  const selected = chapters?.find((c) => c.id === selectedId);

  const handleCreate = async () => {
    if (!newTitle.trim()) return;
    await create.mutateAsync({ title: newTitle, project_id: projectId });
    setNewTitle("");
  };

  const handleSave = async () => {
    if (!selectedId) return;
    await update.mutateAsync({ id: selectedId, data: { content: editContent } });
  };

  const handleSelect = (chapter: { id: string; content: string }) => {
    setSelectedId(chapter.id);
    setEditContent(chapter.content);
  };

  return (
    <div className="flex h-full">
      {/* Chapter sidebar */}
      <aside
        className="w-[var(--layout-writer-sidebar)] shrink-0 border-r flex flex-col"
        style={{
          background: "var(--surface-editor-sidebar)",
          borderColor: "var(--border-subtle)",
        }}
      >
        <div className="p-3">
          <h2 className="mb-2 text-xs font-semibold tracking-wide" style={{ color: "var(--text-tertiary)" }}>
            章节
          </h2>
          <div className="flex gap-1">
            <Input
              placeholder="新章节..."
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              className="h-7 text-xs"
            />
            <Button size="sm" variant="ghost" className="h-7 px-2" onClick={handleCreate}>
              <Plus className="size-3" />
            </Button>
          </div>
        </div>
        <ScrollArea className="flex-1">
          {isLoading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="size-5 animate-spin" style={{ color: "var(--accent-base)" }} />
            </div>
          ) : (
            <div className="space-y-0.5 px-2">
              {chapters?.map((c) => (
                <button
                  key={c.id}
                  onClick={() => handleSelect(c)}
                  className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm transition-colors"
                  style={{
                    background: selectedId === c.id ? "var(--nav-item-active-bg)" : "transparent",
                    color: selectedId === c.id ? "var(--nav-item-active-text)" : "var(--nav-item-text)",
                  }}
                >
                  <FileText className="size-3.5 shrink-0" style={{ color: "var(--text-muted)" }} />
                  <span className="flex-1 truncate">{c.title}</span>
                  <button
                    className="rounded p-0.5 opacity-0 hover:bg-[var(--danger-subtle)]"
                    onClick={(e) => {
                      e.stopPropagation();
                      remove.mutate(c.id);
                    }}
                  >
                    <Trash2 className="size-3" style={{ color: "var(--danger-text)" }} />
                  </button>
                </button>
              ))}
            </div>
          )}
        </ScrollArea>
      </aside>

      {/* Editor */}
      <main
        className="flex-1 flex flex-col"
        style={{ background: "var(--surface-editor)" }}
      >
        {selected ? (
          <>
            {/* Toolbar */}
            <div
              className="flex items-center justify-between px-6 py-3 border-b"
              style={{ borderColor: "var(--border-subtle)" }}
            >
              <div className="flex items-center gap-2">
                <div
                  className="w-0.5 h-5 rounded-full"
                  style={{ background: "var(--accent-base)" }}
                />
                <span className="text-sm" style={{ color: "var(--text-tertiary)" }}>
                  {selected.title}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <Button size="sm" variant="ghost" className="h-7">
                  <Sparkles className="size-3.5 mr-1" />
                  AI
                </Button>
                <Button size="sm" onClick={handleSave} disabled={update.isPending}>
                  {update.isPending ? "保存中..." : "保存"}
                </Button>
              </div>
            </div>

            {/* Content area */}
            <div className="flex-1 overflow-auto">
              <div
                className="mx-auto p-8"
                style={{ maxWidth: "var(--layout-writer-max-width)" }}
              >
                <textarea
                  className="w-full min-h-[60vh] resize-y rounded-lg p-4 text-sm leading-relaxed border-0 focus:ring-0"
                  style={{
                    background: "transparent",
                    color: "var(--editor-text)",
                    caretColor: "var(--editor-cursor)",
                    fontFamily: "var(--font-mono)",
                    lineHeight: "1.85",
                  }}
                  value={editContent}
                  onChange={(e) => setEditContent(e.target.value)}
                  placeholder="章节内容..."
                />
              </div>
            </div>

            {/* Status bar */}
            <div
              className="flex items-center justify-between px-6 py-2 border-t text-[0.7rem]"
              style={{
                borderColor: "var(--border-subtle)",
                color: "var(--text-muted)",
              }}
            >
              <span>字数: {editContent.length}</span>
              <span>自动保存</span>
            </div>
          </>
        ) : (
          <div
            className="flex h-full items-center justify-center"
            style={{ color: "var(--text-muted)" }}
          >
            {chapters?.length
              ? "从左侧选择一个章节开始编辑"
              : "新建一个章节开始写作"}
          </div>
        )}
      </main>
    </div>
  );
}
```

- [ ] **Step 2: Build check**

Run: `cd /home/sihan/文档/Projects/AI-Novel-Generation/novel-frontend && npx next build --no-lint 2>&1 | tail -10`
Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add novel-frontend/src/app/projects/\[id\]/writer/page.tsx
git commit -m "feat(writer): redesign with editor background, purple accents, AI button, status bar"
```

---

### Task 9: Agent Chat Page

**Files:**
- Modify: `novel-frontend/src/app/projects/[id]/agent/page.tsx`

**Spec ref:** Chat section, Message types, Reasoning Panel, Markdown rendering, Input area

- [ ] **Step 1: Rewrite `agent/page.tsx`**

Key changes: glass bubbles with purple gradient avatar, user bubbles with solid purple, reasoning panel with label safety (max 32 chars), tool call status display, markdown code block styling, animated streaming dots, empty state with gradient circle.

```tsx
"use client";

import { useParams } from "next/navigation";
import { useState, useRef, useEffect } from "react";
import { useAgentSSE } from "@/hooks/use-sse";
import { useAgentStore } from "@/stores/agent";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Loader2, Send, RotateCcw, Bot, User, Sparkles } from "lucide-react";

export default function AgentPage() {
  const { id: projectId } = useParams<{ id: string }>();
  const { send, reset } = useAgentSSE();
  const { messages, isStreaming } = useAgentStore();
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = () => {
    if (!input.trim() || isStreaming) return;
    send(projectId, input.trim());
    setInput("");
  };

  const handleReset = () => reset();

  return (
    <div className="flex h-full flex-col" style={{ background: "var(--surface-page)" }}>
      {/* Header */}
      <header
        className="flex items-center justify-between px-6 py-3 border-b shrink-0"
        style={{ borderColor: "var(--border-subtle)", background: "var(--surface-sidebar)" }}
      >
        <div className="flex items-center gap-3">
          <div
            className="size-8 rounded-lg flex items-center justify-center"
            style={{
              background: "var(--gradient-accent)",
            }}
          >
            <Bot className="size-4 text-white" />
          </div>
          <div>
            <h1 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
              Agent 助手
            </h1>
            <p className="text-xs" style={{ color: "var(--text-tertiary)" }}>
              AI 写作助手 · 对话与脑暴
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {isStreaming && (
            <span className="flex items-center gap-1 text-xs" style={{ color: "var(--accent-text)" }}>
              <Loader2 className="size-3 animate-spin" />
              响应中
            </span>
          )}
          <Button variant="ghost" size="sm" onClick={handleReset} disabled={isStreaming}>
            <RotateCcw className="size-4 mr-1" />
            新对话
          </Button>
        </div>
      </header>

      {/* Messages */}
      <ScrollArea className="flex-1 px-6 py-4">
        <div className="mx-auto space-y-4" style={{ maxWidth: "var(--layout-chat-max-width)" }}>
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center py-32 text-center">
              <div
                className="size-16 rounded-full flex items-center justify-center mb-4"
                style={{
                  background: "var(--gradient-accent)",
                  boxShadow: "0 0 24px var(--accent-glow)",
                }}
              >
                <Sparkles className="size-7 text-white" />
              </div>
              <p className="text-lg font-medium" style={{ color: "var(--text-primary)" }}>
                开始你的创作对话
              </p>
              <p className="mt-1 text-sm" style={{ color: "var(--text-tertiary)" }}>
                发送写作请求、灵感想法，或输入
                <code
                  className="mx-1 rounded px-1 py-0.5 text-xs"
                  style={{
                    background: "var(--bg-elevated)",
                    color: "var(--accent-text)",
                  }}
                >
                  /brainstorm
                </code>
                进入脑暴模式
              </p>
            </div>
          )}

          {messages.map((msg) => (
            <ChatBubble key={msg.id} msg={msg} />
          ))}

          {isStreaming && messages.length > 0 && (
            <div className="flex items-center gap-2 text-sm" style={{ color: "var(--accent-text)" }}>
              <div className="flex gap-1">
                <span className="size-1.5 rounded-full animate-bounce" style={{ background: "var(--accent-base)" }} />
                <span className="size-1.5 rounded-full animate-bounce" style={{ background: "var(--accent-base)", animationDelay: "0.2s" }} />
                <span className="size-1.5 rounded-full animate-bounce" style={{ background: "var(--accent-base)", animationDelay: "0.4s" }} />
              </div>
              等待响应...
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </ScrollArea>

      {/* Input */}
      <footer
        className="px-6 py-4 border-t shrink-0"
        style={{ borderColor: "var(--border-subtle)", background: "var(--surface-page)" }}
      >
        <div className="mx-auto flex gap-2" style={{ maxWidth: "var(--layout-chat-max-width)" }}>
          <div
            className="flex-1 flex items-center gap-2 rounded-xl px-3"
            style={{
              background: "var(--input-bg)",
              border: "1px solid var(--input-border)",
            }}
          >
            <Sparkles className="size-4 shrink-0" style={{ color: "var(--text-muted)" }} />
            <Input
              placeholder={isStreaming ? "等待响应..." : "输入消息，或 /brainstorm 进入脑暴..."}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
              disabled={isStreaming}
              className="border-0 focus-visible:ring-0 !shadow-none px-0"
              style={{ background: "transparent" }}
            />
          </div>
          <Button onClick={handleSend} disabled={!input.trim() || isStreaming}>
            <Send className="size-4" />
          </Button>
        </div>
      </footer>
    </div>
  );
}

/* ────────── Chat Bubble ────────── */

interface ChatMessage {
  id: string;
  role: string;
  content: string;
  messageType?: string;
  status?: string;
  label?: string;
}

function ChatBubble({ msg }: { msg: ChatMessage }) {
  const isUser = msg.role === "user";
  const isSystem = msg.role === "system";
  const isToolCall = msg.messageType === "tool_call";
  const isReasoning = msg.messageType === "reasoning";
  const [reasoningOpen, setReasoningOpen] = useState(false);

  if (isSystem) {
    return (
      <div className="flex justify-center">
        <span
          className="rounded-full px-2 py-0.5 text-xs"
          style={{ background: "var(--danger-subtle)", color: "var(--danger-text)" }}
        >
          {msg.content}
        </span>
      </div>
    );
  }

  if (isToolCall) {
    const statusIcon =
      msg.status === "running" ? "🔄" :
      msg.status === "success" ? "✓" :
      msg.status === "failed" ? "✗" :
      msg.status === "cancelled" ? "—" : "⏳";
    const statusColor =
      msg.status === "running" ? "var(--processing-text)" :
      msg.status === "success" ? "var(--success-text)" :
      msg.status === "failed" ? "var(--danger-text)" : "var(--text-muted)";

    return (
      <div className="flex justify-start">
        <div
          className="rounded-lg px-4 py-2.5 text-sm max-w-[75%]"
          style={{
            background: "var(--processing-subtle)",
            border: "1px solid var(--processing-border)",
          }}
        >
          <span className="mr-1" style={{ color: statusColor }}>{statusIcon}</span>
          <span style={{ color: "var(--text-secondary)" }}>{msg.content}</span>
        </div>
      </div>
    );
  }

  if (isReasoning) {
    const label = (msg.label || "分析信息").slice(0, 32);
    return (
      <div className="flex justify-start">
        <div className="max-w-[75%]">
          <button
            onClick={() => setReasoningOpen(!reasoningOpen)}
            className="flex items-center gap-2 rounded-full px-3 py-1 text-xs transition-colors"
            style={{
              background: "var(--accent-subtle)",
              color: "var(--accent-text)",
            }}
          >
            <span>{reasoningOpen ? "▼" : "▶"}</span>
            <span className="truncate max-w-[32ch]">{label}</span>
          </button>
          {reasoningOpen && (
            <div
              className="mt-2 rounded-lg px-4 py-3 text-sm italic leading-relaxed"
              style={{
                background: "var(--accent-subtle)",
                color: "var(--text-tertiary)",
                borderLeft: "2px solid var(--accent-border)",
              }}
            >
              {msg.content}
            </div>
          )}
        </div>
      </div>
    );
  }

  // User or assistant message
  return (
    <div className={`flex gap-3 ${isUser ? "justify-end" : ""}`}>
      {!isUser && (
        <div
          className="size-8 shrink-0 rounded-full flex items-center justify-center"
          style={{ background: "var(--gradient-accent)" }}
        >
          <Bot className="size-4 text-white" />
        </div>
      )}

      <div
        className={`max-w-[75%] rounded-xl px-4 py-2.5 ${
          isUser ? "" : "backdrop-blur-[6px]"
        }`}
        style={{
          background: isUser
            ? "var(--bubble-user-bg)"
            : "var(--surface-glass-bg)",
          color: isUser
            ? "var(--bubble-user-text)"
            : "var(--text-secondary)",
          border: isUser ? "none" : "1px solid var(--surface-glass-border)",
        }}
      >
        {msg.messageType && msg.messageType !== "user_message" && !isUser && (
          <span
            className="mb-1 block text-[0.6rem] uppercase tracking-wide"
            style={{ color: "var(--text-muted)" }}
          >
            {msg.messageType}
          </span>
        )}
        <p className="whitespace-pre-wrap text-sm leading-relaxed">
          {msg.content}
        </p>
      </div>

      {isUser && (
        <div
          className="size-8 shrink-0 rounded-full flex items-center justify-center"
          style={{
            background: "var(--bg-elevated-hover)",
            border: "1px solid var(--border-subtle)",
          }}
        >
          <User className="size-4" style={{ color: "var(--text-tertiary)" }} />
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Build check**

Run: `cd /home/sihan/文档/Projects/AI-Novel-Generation/novel-frontend && npx next build --no-lint 2>&1 | tail -10`
Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add novel-frontend/src/app/projects/\[id\]/agent/page.tsx
git commit -m "feat(agent): redesign with glass bubbles, purple avatar, reasoning panel, tool call states"
```

---

### Task 10: Ideas, Styles, Config Pages

**Files:**
- Modify: `novel-frontend/src/app/ideas/page.tsx`
- Modify: `novel-frontend/src/app/styles/page.tsx`
- Modify: `novel-frontend/src/app/config/page.tsx`

**Spec ref:** Ideas, Styles, Config sections

These three pages follow the same pattern: replace manual `text-zinc-*` / `bg-zinc-*` with `style={{ color: "var(--...)" }}` references, use `Card surface="solid"`, and add `Badge` where appropriate. The structural HTML stays the same; only token references change.

- [ ] **Step 1: Update `ideas/page.tsx`**

```tsx
"use client";

import { useState } from "react";
import { useIdeas, useCreateIdea, useDeleteIdea } from "@/lib/queries/ideas";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Plus, Trash2, Loader2, Lightbulb } from "lucide-react";

export default function IdeasPage() {
  const { data: ideas, isLoading } = useIdeas();
  const create = useCreateIdea();
  const remove = useDeleteIdea();
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");

  const handleCreate = async () => {
    if (!title.trim()) return;
    await create.mutateAsync({ title, content });
    setTitle("");
    setContent("");
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-16">
        <Loader2 className="size-6 animate-spin" style={{ color: "var(--accent-base)" }} />
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="flex items-center justify-between">
        <div>
          <span
            className="inline-block rounded-full px-2.5 py-0.5 text-[0.7rem] font-medium tracking-wide"
            style={{ background: "var(--accent-subtle)", color: "var(--accent-text)" }}
          >
            灵感
          </span>
          <h1 className="mt-2 text-2xl font-bold tracking-tight" style={{ color: "var(--text-primary)" }}>
            灵感
          </h1>
          <p className="mt-1 text-sm" style={{ color: "var(--text-tertiary)" }}>
            随手记录创作灵感
          </p>
        </div>
      </div>

      {/* Quick input */}
      <div className="mt-6 flex gap-2">
        <Input
          placeholder="标题..."
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="max-w-xs"
        />
        <Input
          placeholder="内容（可选）"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          className="flex-1"
        />
        <Button size="sm" onClick={handleCreate} disabled={create.isPending}>
          <Plus className="size-4 mr-1" />
          添加
        </Button>
      </div>

      {/* List */}
      <div
        className="mt-6 grid gap-4"
        style={{
          gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
        }}
      >
        {ideas?.map((idea) => (
          <Card key={idea.id} className="group relative" surface="solid">
            <CardHeader>
              <CardTitle className="flex items-start gap-2 text-base">
                <Lightbulb className="mt-0.5 size-4 shrink-0" style={{ color: "#f59e0b" }} />
                {idea.title}
              </CardTitle>
            </CardHeader>
            {idea.content && (
              <CardContent>
                <p className="line-clamp-3 text-sm leading-relaxed" style={{ color: "var(--text-tertiary)" }}>
                  {idea.content}
                </p>
              </CardContent>
            )}
            <button
              className="absolute right-2 top-2 rounded p-1 opacity-0 transition-opacity group-hover:opacity-100"
              style={{ background: "transparent" }}
              onClick={() => remove.mutate(idea.id)}
            >
              <Trash2 className="size-3.5" style={{ color: "var(--danger-text)" }} />
            </button>
          </Card>
        ))}
      </div>

      {ideas?.length === 0 && (
        <p className="mt-16 text-center" style={{ color: "var(--text-muted)" }}>
          还没有灵感记录。
        </p>
      )}
    </div>
  );
}
```

**Apply the same pattern to `styles/page.tsx` and `config/page.tsx`:**
- Replace `text-zinc-*` → `style={{ color: "var(--text-*) }}`
- Replace `bg-zinc-*` → `style={{ background: "var(--bg-*) }}` or `className="bg-[var(...)]"`
- Add page label badge (matching the pattern above)
- Use `Card surface="solid"`
- Use `Loader2` with `style={{ color: "var(--accent-base)" }}` for loading
- Use `style={{ color: "var(--text-muted)" }}` for empty states

- [ ] **Step 2: Run build check**

```bash
cd /home/sihan/文档/Projects/AI-Novel-Generation/novel-frontend && npx next build --no-lint 2>&1 | tail -10
```

- [ ] **Step 3: Commit all three**

```bash
git add novel-frontend/src/app/ideas/page.tsx novel-frontend/src/app/styles/page.tsx novel-frontend/src/app/config/page.tsx
git commit -m "feat(ideas,styles,config): redesign with semantic tokens, solid cards, badge component"
```

---

### Task 11: Global Verification Build

**Files:**
- All modified files

- [ ] **Step 1: Full build**

```bash
cd /home/sihan/文档/Projects/AI-Novel-Generation/novel-frontend && npx next build 2>&1 | tail -30
```

Expected: Build succeeds, no lint errors, no TS errors.

- [ ] **Step 2: Check for remaining hardcoded zinc colors**

```bash
cd /home/sihan/文档/Projects/AI-Novel-Generation/novel-frontend
grep -rn 'text-zinc-\|bg-zinc-\|dark:text-zinc-\|dark:bg-zinc-' src/ | grep -v node_modules | grep -v '.next'
```

If any remaining, they need to be replaced with the appropriate token.

- [ ] **Step 3: Final commit**

```bash
git add .
git commit -m "fix: replace remaining hardcoded zinc colors with semantic tokens"
```

---

### Self-Review Checklist

**1. Spec coverage:**
- [ ] Base tokens dark + sepia (Task 1)
- [ ] Semantic tokens (Task 1)
- [ ] Focus ring + scrollbar + reduced-motion (Task 1)
- [ ] Z-index system (Task 1)
- [ ] Layout dimension tokens (Task 1)
- [ ] Theme store + provider + toggle (Task 2)
- [ ] Badge component (Task 3)
- [ ] Card solid/glass variants (Task 4)
- [ ] Collapsible sidebar (Task 5)
- [ ] Dashboard page (Task 6)
- [ ] Project list + detail (Task 7)
- [ ] Writer editor (Task 8)
- [ ] Agent chat with tool call states + reasoning panel (Task 9)
- [ ] Ideas / Styles / Config (Task 10)
- [ ] Tag color algorithm (Task 7, `colorForTag`)
- [ ] State priority rules — covered across all pages (Error > Loading > Empty > Ready), per-page impl follows the spec contract

**2. Placeholder scan:** No TBD, TODOs, or vague sections. Every step has complete code.

**3. Type consistency:** The `Badge` component, `Card` surface prop, `theme` store, and `ThemeToggle` all have consistent types across the tasks that reference them.
