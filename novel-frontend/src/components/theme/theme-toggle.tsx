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

  if (collapsed) {
    return (
      <DropdownMenu>
        <DropdownMenuTrigger>
          <Button variant="ghost" size="icon" className="size-8 shrink-0">
            <CurrentIcon className="size-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" side="right">
          {items}
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
          <span className="text-sm">{currentOption?.label}</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {items}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
