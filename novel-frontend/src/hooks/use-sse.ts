"use client";

import { useEffect, useCallback } from "react";
import { useAgentStore } from "@/stores/agent";

/**
 * Manage an SSE connection to the agent chat endpoint.
 * Agent SSE is at POST /project/{project_id}/agent/chat/stream
 * (not under /api/ — use absolute backend URL).
 */
const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export function useAgentSSE() {
  const { taskId, appendMessage, setConnected, setStreaming } =
    useAgentStore();

  const connect = useCallback(
    async (projectId: string, message: string) => {
      setStreaming(true);

      const res = await fetch(
        `${BACKEND}/project/${projectId}/agent/chat/stream`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message }),
        },
      );

      if (!res.ok || !res.body) {
        setStreaming(false);
        return;
      }

      setConnected(true);
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.trim()) continue;

          // SSE format: "event: <type>\ndata: <json>\n"
          const dataMatch = line.match(/^data:\s*(.+)$/m);
          if (!dataMatch) continue;

          try {
            const payload = JSON.parse(dataMatch[1]);
            if (payload.type === "done") continue;

            appendMessage({
              id: crypto.randomUUID(),
              role: "assistant",
              content:
                payload.text ?? payload.summary ?? payload.content ?? "",
              messageType: payload.type,
              sequence: payload.sequence ?? 0,
            });
          } catch {
            // skip unparseable chunks
          }
        }
      }

      setStreaming(false);
    },
    [appendMessage, setConnected, setStreaming],
  );

  return { connect };
}
