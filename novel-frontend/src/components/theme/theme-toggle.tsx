"use client";

import { useThemeStore } from "@/stores/theme";
import { Moon, SunMedium, Monitor } from "lucide-react";
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

/* Shared ghost-button styles for the trigger (prevents <button> nested inside <button>) */
const triggerBase =
  "inline-flex items-center justify-center rounded-lg text-sm font-medium whitespace-nowrap transition-all outline-none select-none cursor-pointer";

function ThemeTrigger({ collapsed, currentIcon, label }: { collapsed: boolean; currentIcon: React.ReactNode; label?: string }) {
  return (
    <span
      className={triggerBase}
      style={{
        gap: collapsed ? 0 : "0.375rem",
        height: collapsed ? "2rem" : "1.75rem",
        padding: collapsed ? "0" : "0 0.625rem",
        width: collapsed ? "2rem" : "100%",
        justifyContent: collapsed ? "center" : "flex-start",
        color: "var(--text-secondary)",
        background: "transparent",
      }}
      onMouseEnter={(e) => { e.currentTarget.style.background = "var(--bg-elevated-hover)"; }}
      onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; }}
    >
      {currentIcon}
      {!collapsed && label && <span className="text-sm">{label}</span>}
    </span>
  );
}

export function ThemeToggle({ collapsed = false }: { collapsed?: boolean }) {
  const theme = useThemeStore((s) => s.theme);
  const resolved = useThemeStore((s) => s.resolved);
  const setTheme = useThemeStore((s) => s.setTheme);

  const currentOption = THEME_OPTIONS.find((o) => o.value === resolved);
  const CurrentIcon = currentOption?.icon ?? Moon;

  const items = THEME_OPTIONS.map((opt) => (
    <DropdownMenuItem
      key={opt.value}
      onClick={() => setTheme(opt.value)}
      className={theme === opt.value ? "text-accent-foreground" : ""}
    >
      <opt.icon className="mr-2 size-4" />
      {opt.label}
    </DropdownMenuItem>
  ));

  return (
    <DropdownMenu>
      <DropdownMenuTrigger>
        <ThemeTrigger
          collapsed={collapsed}
          currentIcon={<CurrentIcon className="size-4" />}
          label={currentOption?.label}
        />
      </DropdownMenuTrigger>
      <DropdownMenuContent align={collapsed ? "start" : "end"} side={collapsed ? "right" : "bottom"}>
        {items}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
