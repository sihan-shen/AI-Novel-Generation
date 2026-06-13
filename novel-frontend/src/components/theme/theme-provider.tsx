"use client";

import { useEffect } from "react";
import { useThemeStore } from "@/stores/theme";

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const resolved = useThemeStore((s) => s.resolved);

  useEffect(() => {
    document.documentElement.classList.remove("dark", "sepia");
    document.documentElement.classList.add(resolved);
    document.documentElement.setAttribute("data-theme", resolved);
  }, [resolved]);

  return <>{children}</>;
}
