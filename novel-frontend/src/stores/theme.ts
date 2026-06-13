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
  root.setAttribute("data-theme", resolved);
  root.classList.remove("dark", "sepia");
  root.classList.add(resolved);
}

export const useThemeStore = create<ThemeState>((set) => {
  const stored = getStored();
  const resolved = resolveTheme(stored);
  if (typeof window !== "undefined") applyTheme(resolved);

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

      if (t === "system") {
        const mq = window.matchMedia("(prefers-color-scheme: light)");
        const handler = () => {
          const nr = resolveTheme("system");
          applyTheme(nr);
          set({ resolved: nr });
        };
        mq.addEventListener("change", handler);
      }
    },
  };
});
