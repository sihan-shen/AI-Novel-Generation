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
        <DropdownMenuTrigger>
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
      <DropdownMenuTrigger>
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
