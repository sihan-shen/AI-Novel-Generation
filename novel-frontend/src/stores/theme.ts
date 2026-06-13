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

/* ────────── System listener management ────────── */
let systemListener: { mq: MediaQueryList; handler: () => void } | null = null;

function listenToSystem(set: (state: Partial<ThemeState>) => void) {
  // Clean up previous listener first
  if (systemListener) {
    systemListener.mq.removeEventListener("change", systemListener.handler);
    systemListener = null;
  }
  const mq = window.matchMedia("(prefers-color-scheme: light)");
  const handler = () => {
    const r = resolveTheme("system");
    applyTheme(r);
    set({ resolved: r });
  };
  mq.addEventListener("change", handler);
  systemListener = { mq, handler };
}

function unlistenSystem() {
  if (systemListener) {
    systemListener.mq.removeEventListener("change", systemListener.handler);
    systemListener = null;
  }
}

export const useThemeStore = create<ThemeState>((set) => {
  const stored = getStored();
  const resolved = resolveTheme(stored);
  if (typeof window !== "undefined") applyTheme(resolved);

  // Set up initial listener if stored was "system"
  if (typeof window !== "undefined" && stored === "system") {
    listenToSystem(set);
  }

  return {
    theme: stored,
    resolved,
    setTheme: (t: Theme) => {
      localStorage.setItem(STORAGE_KEY, t);
      const r = resolveTheme(t);
      applyTheme(r);
      set({ theme: t, resolved: r });

      // Manage system listener based on new theme
      if (t === "system") {
        listenToSystem(set);
      } else {
        unlistenSystem();
      }
    },
  };
});
