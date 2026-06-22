export const toneStyles: Record<string, { bg: string; text: string; glow: string }> = {
  violet: {
    bg: "var(--accent-subtle)",
    text: "var(--accent-text)",
    glow: "var(--accent-glow)",
  },
  amber: {
    bg: "var(--warning-subtle)",
    text: "var(--warning-text)",
    glow: "rgba(245,158,11,0.12)",
  },
  emerald: {
    bg: "var(--success-subtle)",
    text: "var(--success-text)",
    glow: "rgba(34,197,94,0.12)",
  },
  cyan: {
    bg: "var(--info-subtle)",
    text: "var(--info-text)",
    glow: "rgba(59,130,246,0.12)",
  },
};

export const STATUS_BADGE: Record<
  string,
  { label: string; variant: "default" | "processing" | "success" }
> = {
  draft: { label: "草稿", variant: "default" },
  writing: { label: "写作中", variant: "processing" },
  completed: { label: "已完成", variant: "success" },
};

export const STATUS_LABEL: Record<string, string> = {
  draft: "草稿",
  writing: "写作中",
  completed: "已完成",
};
