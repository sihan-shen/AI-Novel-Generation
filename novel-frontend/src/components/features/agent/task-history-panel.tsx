"use client";

import { useEffect, useState } from "react";

export interface AgentTaskSummary {
  id: string;
  task_type: string;
  status: string;
  total_steps?: number;
  total_tokens?: number;
  created_at: string | null;
  completed_at: string | null;
}

interface TaskHistoryPanelProps {
  projectId: string;
}

export function TaskHistoryPanel({ projectId }: TaskHistoryPanelProps) {
  const [tasks, setTasks] = useState<AgentTaskSummary[]>([]);
  const [loaded, setLoaded] = useState(false);
  const loading = !loaded;

  useEffect(() => {
    if (!projectId) return;
    let cancelled = false;
    fetch(`/api/project/${projectId}/agent/tasks`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((body: { data?: { tasks?: AgentTaskSummary[] } }) => {
        if (cancelled) return;
        setTasks(body?.data?.tasks ?? []);
        setLoaded(true);
      })
      .catch(() => {
        if (cancelled) return;
        setTasks([]);
        setLoaded(true);
      });
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  return (
    <details
      className="border-t shrink-0 group"
      style={{ borderColor: "var(--border-subtle)", background: "var(--surface-sidebar)" }}
      data-testid="task-history-panel"
    >
      <summary
        className="px-6 py-2 text-xs cursor-pointer select-none list-none flex items-center gap-2"
        style={{ color: "var(--text-secondary)" }}
      >
        <span className="text-[0.6rem] transition-transform group-open:rotate-90">▶</span>
        历史任务
        <span style={{ color: "var(--text-muted)" }}>
          ({loading ? "加载中…" : tasks.length})
        </span>
      </summary>
      <div className="px-6 pb-3 max-h-48 overflow-y-auto">
        {!loading && tasks.length === 0 && (
          <p className="text-xs py-1" style={{ color: "var(--text-muted)" }}>
            暂无历史任务
          </p>
        )}
        <ul className="space-y-1">
          {tasks.map((t) => {
            const statusColor =
              t.status === "completed"
                ? "var(--accent-text)"
                : t.status === "failed"
                  ? "#ef4444"
                  : t.status === "running"
                    ? "var(--text-secondary)"
                    : "var(--text-muted)";
            return (
              <li
                key={t.id}
                className="text-xs flex items-center gap-2"
                style={{ color: "var(--text-tertiary)" }}
              >
                <span className="font-mono">{t.task_type}</span>
                <span style={{ color: "var(--text-muted)" }}>·</span>
                <span style={{ color: statusColor }}>{t.status}</span>
                <span style={{ color: "var(--text-muted)" }}>·</span>
                <span className="font-mono">{t.created_at ?? "—"}</span>
                {typeof t.total_steps === "number" && (
                  <>
                    <span style={{ color: "var(--text-muted)" }}>·</span>
                    <span>{t.total_steps} 步</span>
                  </>
                )}
              </li>
            );
          })}
        </ul>
      </div>
    </details>
  );
}
