"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api-client";
import { useAgentStore, type SuggestionEvent } from "@/stores/agent";

interface SuggestionCardProps {
  suggestion: SuggestionEvent;
  projectId: string;
}

export function SuggestionCard({ suggestion, projectId }: SuggestionCardProps) {
  const removeSuggestion = useAgentStore((s) => s.removeSuggestion);
  const [handled, setHandled] = useState(false);
  const [modification, setModification] = useState("");
  const [showModify, setShowModify] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  if (handled) {
    return (
      <div className="flex justify-start">
        <div
          className="rounded-lg px-4 py-3 text-sm max-w-[75%] w-full"
          style={{
            background: "var(--surface-glass-bg)",
            border: "1px solid var(--accent-border)",
          }}
        >
          <span
            className="rounded-full px-2 py-0.5 text-[0.65rem] uppercase tracking-wide"
            style={{ background: "var(--accent-subtle)", color: "var(--accent-text)" }}
          >
            已处理
          </span>
        </div>
      </div>
    );
  }

  async function handleConfirm(action: "approve" | "reject" | "modify") {
    setIsLoading(true);
    try {
      await api.post(`project/${projectId}/agent/chat/confirm`, {
        json: {
          confirm_id: suggestion.id,
          action,
          ...(action === "modify" ? { modification } : {}),
        },
      });
      setHandled(true);
      removeSuggestion(suggestion.id);
    } catch {
      /* no-op */
    } finally {
      setIsLoading(false);
    }
  }

  async function handleSaveInspiration() {
    setIsLoading(true);
    try {
      await api.post(`project/${projectId}/agent/inspirations/confirm`, {
        json: { inspiration_ids: [suggestion.id] },
      });
      setHandled(true);
      removeSuggestion(suggestion.id);
    } catch {
      /* no-op */
    } finally {
      setIsLoading(false);
    }
  }

  function handleDiscard() {
    removeSuggestion(suggestion.id);
  }

  const isConfirm = suggestion.type === "confirm_request";

  return (
    <div className="flex justify-start">
      <div
        className="rounded-lg px-4 py-3 text-sm max-w-[75%] w-full"
        style={{
          background: "var(--surface-glass-bg)",
          border: "1px solid var(--accent-border)",
        }}
      >
        <div className="flex items-center gap-2 mb-2">
          <span
            className="rounded-full px-2 py-0.5 text-[0.65rem] uppercase tracking-wide"
            style={{ background: "var(--accent-subtle)", color: "var(--accent-text)" }}
          >
            {isConfirm ? "确认请求" : "建议"}
          </span>
          {suggestion.tool && (
            <span className="text-xs" style={{ color: "var(--text-muted)" }}>
              {suggestion.tool}
            </span>
          )}
        </div>

        {suggestion.summary && (
          <p className="mb-3 leading-relaxed" style={{ color: "var(--text-secondary)" }}>
            {suggestion.summary}
          </p>
        )}

        {suggestion.args && (
          <pre
            className="mb-3 rounded px-2 py-1 text-xs overflow-x-auto"
            style={{ background: "var(--bg-elevated)", color: "var(--text-secondary)" }}
          >
            {JSON.stringify(suggestion.args, null, 2)}
          </pre>
        )}

        {isConfirm ? (
          <div className="space-y-2">
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => handleConfirm("approve")}
                disabled={isLoading}
              >
                批准
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => handleConfirm("reject")}
                disabled={isLoading}
              >
                拒绝
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => setShowModify((v) => !v)}
                disabled={isLoading}
              >
                修改
              </Button>
            </div>
            {showModify && (
              <div className="flex gap-2">
                <Input
                  placeholder="输入修改意见"
                  value={modification}
                  onChange={(e) => setModification(e.target.value)}
                  className="h-8 text-xs"
                />
                <Button
                  size="sm"
                  variant="default"
                  onClick={() => handleConfirm("modify")}
                  disabled={isLoading || !modification.trim()}
                >
                  提交修改
                </Button>
              </div>
            )}
          </div>
        ) : (
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={handleSaveInspiration}
              disabled={isLoading}
            >
              保存
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={handleDiscard}
              disabled={isLoading}
            >
              丢弃
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
