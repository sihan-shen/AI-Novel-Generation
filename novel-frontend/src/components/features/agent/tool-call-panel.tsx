"use client";

import { useState } from "react";
import type { ToolCallEvent } from "@/stores/agent";

export function ToolCallPanel({ toolCall }: { toolCall: ToolCallEvent }) {
  const [open, setOpen] = useState(false);

  const statusIcon =
    toolCall.status === "running"
      ? "🔄"
      : toolCall.status === "success"
        ? "✓"
        : toolCall.status === "failed"
          ? "✗"
          : toolCall.status === "cancelled"
            ? "—"
            : "⏳";

  const statusColor =
    toolCall.status === "running"
      ? "var(--processing-text)"
      : toolCall.status === "success"
        ? "var(--success-text)"
        : toolCall.status === "failed"
          ? "var(--danger-text)"
          : "var(--text-muted)";

  return (
    <div className="flex justify-start">
      <div
        className="rounded-lg px-4 py-2.5 text-sm max-w-[75%] w-full"
        style={{
          background: "var(--processing-subtle)",
          border: "1px solid var(--processing-border)",
        }}
      >
        <button
          onClick={() => setOpen(!open)}
          aria-expanded={open}
          aria-label={open ? `收起工具调用 ${toolCall.tool}` : `展开工具调用 ${toolCall.tool}`}
          className="flex items-center gap-2 w-full text-left"
        >
          <span style={{ color: statusColor }}>{statusIcon}</span>
          <span className="font-medium" style={{ color: "var(--text-secondary)" }}>
            {toolCall.tool}
          </span>
          <span className="text-xs ml-auto" style={{ color: "var(--text-muted)" }}>
            {open ? "▼" : "▶"}
          </span>
        </button>

        {open && (
          <div className="mt-2 space-y-2 text-xs">
            <div>
              <span style={{ color: "var(--text-muted)" }}>参数:</span>
              <pre
                className="mt-1 rounded px-2 py-1 overflow-x-auto"
                style={{ background: "var(--bg-elevated)", color: "var(--text-secondary)" }}
              >
                {JSON.stringify(toolCall.args, null, 2)}
              </pre>
            </div>
            {toolCall.result !== undefined && (
              <div>
                <span style={{ color: "var(--text-muted)" }}>结果:</span>
                <pre
                  className="mt-1 rounded px-2 py-1 overflow-x-auto"
                  style={{ background: "var(--bg-elevated)", color: "var(--text-secondary)" }}
                >
                  {toolCall.result}
                </pre>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
