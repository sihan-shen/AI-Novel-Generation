"use client";

import { useCallback } from "react";
import { useAgentStore } from "@/stores/agent";

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

/**
 * Hook for POST-based SSE connection to the agent chat stream.
 * The backend agent endpoint uses POST (not GET), so we use
 * fetch + ReadableStream instead of EventSource.
 */
export function useAgentSSE() {
  const { appendMessage, setConnected, setStreaming, setTaskId, reset } =
    useAgentStore();

  const send = useCallback(
    async (projectId: string, message: string) => {
      setStreaming(true);

      // Add user message immediately
      appendMessage({
        id: crypto.randomUUID(),
        role: "user",
        content: message,
        sequence: Date.now(),
      });

      try {
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
          appendMessage({
            id: crypto.randomUUID(),
            role: "system",
            content: `请求失败: ${res.status}`,
            messageType: "error",
            sequence: Date.now(),
          });
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
          const lines = buffer.split("\n");
          // Keep the last partial line in the buffer
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            const jsonStr = line.slice(6); // strip "data: " prefix

            if (jsonStr === "[DONE]") continue;

            try {
              const payload = JSON.parse(jsonStr);

              if (payload.sequence) {
                appendMessage({
                  id: crypto.randomUUID(),
                  role: "assistant",
                  content: extractContent(payload),
                  messageType: payload.type ?? payload.messageType,
                  sequence: payload.sequence,
                });
              }
            } catch {
              // skip unparseable
            }
          }
        }
      } catch (err) {
        appendMessage({
          id: crypto.randomUUID(),
          role: "system",
          content: `连接错误: ${err instanceof Error ? err.message : "未知错误"}`,
          messageType: "error",
          sequence: Date.now(),
        });
      } finally {
        setStreaming(false);
        setConnected(false);
      }
    },
    [appendMessage, setConnected, setStreaming],
  );

  return { send, reset };
}

/** Extract human-readable content from various SSE event shapes. */
function extractContent(payload: Record<string, unknown>): string {
  if (typeof payload.text === "string") return payload.text;
  if (typeof payload.summary === "string") return payload.summary;
  if (typeof payload.content === "string") return payload.content;
  if (typeof payload.message === "string") return payload.message;
  if (typeof payload.tool === "string") return `[工具] ${payload.tool}`;
  if (payload.type === "agent_start")
    return `Agent 已启动: ${payload.agent ?? ""}`;
  return JSON.stringify(payload);
}
