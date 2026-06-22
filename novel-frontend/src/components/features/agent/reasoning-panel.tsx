"use client";

import { useState } from "react";
import type { ReasoningEvent } from "@/stores/agent";

export function ReasoningPanel({ reasoning }: { reasoning: ReasoningEvent }) {
  const [open, setOpen] = useState(false);
  const label = reasoning.label.slice(0, 32);

  return (
    <div className="flex justify-start">
      <div className="max-w-[75%]">
        <button
          onClick={() => setOpen(!open)}
          aria-expanded={open}
          aria-label={open ? "收起推理" : "展开推理"}
          className="flex items-center gap-2 rounded-full px-3 py-1 text-xs transition-colors"
          style={{
            background: "var(--accent-subtle)",
            color: "var(--accent-text)",
          }}
        >
          <span>{open ? "▼" : "▶"}</span>
          <span className="truncate max-w-[32ch]">{label}</span>
        </button>
        {open && (
          <div
            className="mt-2 rounded-lg px-4 py-3 text-sm italic leading-relaxed"
            style={{
              background: "var(--accent-subtle)",
              color: "var(--text-tertiary)",
              borderLeft: "2px solid var(--accent-border)",
            }}
          >
            {reasoning.content}
          </div>
        )}
      </div>
    </div>
  );
}
