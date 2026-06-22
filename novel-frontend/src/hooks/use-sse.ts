"use client";

import { useCallback, useRef } from "react";
import { useAgentStore, type ChatRequest } from "@/stores/agent";

interface SSEEvent {
  event: string;
  data: Record<string, unknown>;
}

/**
 * Hook for POST-based SSE connection to the agent chat stream.
 * The backend agent endpoint uses POST (not GET), so we use
 * fetch + ReadableStream instead of EventSource.
 */
export function useAgentSSE() {
  const {
    appendMessage,
    appendToolCall,
    updateToolCallStatus,
    appendReasoning,
    appendSuggestion,
    setOrchestratorState,
    setProgress,
    setTaskId,
    setStreaming,
    updateLastAssistantMessage,
    setHandoffSummary,
    reset,
  } = useAgentStore();

  const abortControllerRef = useRef<AbortController | null>(null);

  const send = useCallback(
    async (projectId: string, request: ChatRequest) => {
      setStreaming(true);
      abortControllerRef.current = new AbortController();

      // Add user message immediately
      appendMessage({
        id: crypto.randomUUID(),
        role: "user",
        content: request.message,
        sequence: Date.now(),
      });

      try {
        const res = await fetch(
          `/api/project/${projectId}/agent/chat/stream`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(request),
            signal: abortControllerRef.current.signal,
          },
        );

        if (!res.ok || !res.body) {
          setStreaming(false);
          appendMessage({
            id: crypto.randomUUID(),
            role: "system",
            content: `请求失败: ${res.status}`,
            sequence: Date.now(),
          });
          return;
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          // SSE messages are separated by blank lines (\n\n)
          const chunks = buffer.split("\n\n");
          // Keep the last partial chunk in the buffer
          buffer = chunks.pop() || "";

          for (const chunk of chunks) {
            if (!chunk.trim()) continue;
            const sseEvent = parseSSEChunk(chunk);
            if (!sseEvent) continue;
            handleEvent(sseEvent);
          }
        }

        // Process any remaining data in the buffer
        if (buffer.trim()) {
          const sseEvent = parseSSEChunk(buffer);
          if (sseEvent) {
            handleEvent(sseEvent);
          }
        }
      } catch (err) {
        if (err instanceof Error && err.name === "AbortError") {
          appendMessage({
            id: crypto.randomUUID(),
            role: "system",
            content: "请求已取消",
            sequence: Date.now(),
          });
        } else {
          appendMessage({
            id: crypto.randomUUID(),
            role: "system",
            content: `连接错误: ${err instanceof Error ? err.message : "未知错误"}`,
            sequence: Date.now(),
          });
        }
      } finally {
        setStreaming(false);
        abortControllerRef.current = null;
      }

      function handleEvent({ event, data }: SSEEvent) {
        switch (event) {
          case "agent_start": {
            const tid = typeof data.task_id === "string" ? data.task_id : null;
            setTaskId(tid);
            const state =
              typeof data.state === "string" ? data.state : "IDLE";
            setOrchestratorState(state);
            break;
          }

          case "text_delta": {
            const text =
              typeof data.content === "string"
                ? data.content
                : typeof data.text === "string"
                  ? data.text
                  : "";
            if (text) {
              updateLastAssistantMessage(text);
            }
            break;
          }

          case "agent_output":
          case "brainstorm_response":
          case "brainstorm_end":
          case "brainstorm_handoff": {
            const text = extractContent(data);
            appendMessage({
              id: crypto.randomUUID(),
              role: "assistant",
              content: text,
              sequence: typeof data.sequence === "number" ? data.sequence : Date.now(),
            });
            const summary =
              typeof data.summary === "string"
                ? data.summary
                : text;
            setHandoffSummary(summary);
            break;
          }

          case "tool_call": {
            const tcId =
              typeof data.tool_call_id === "string"
                ? data.tool_call_id
                : crypto.randomUUID();
            appendToolCall({
              id: tcId,
              tool: typeof data.tool === "string" ? data.tool : "unknown",
              args:
                typeof data.args === "object" && data.args !== null
                  ? (data.args as Record<string, unknown>)
                  : {},
              status: "running",
              sequence: typeof data.sequence === "number" ? data.sequence : Date.now(),
            });
            break;
          }

          case "tool_result": {
            const tcId =
              typeof data.tool_call_id === "string"
                ? data.tool_call_id
                : "";
            const success = data.success === true;
            const resultText = extractContent(data);
            if (tcId) {
              updateToolCallStatus(
                tcId,
                success ? "success" : "failed",
                resultText,
              );
            }
            break;
          }

          case "orchestrator_thought": {
            const text =
              typeof data.text === "string"
                ? data.text
                : extractContent(data);
            appendReasoning({
              id: crypto.randomUUID(),
              label: typeof data.label === "string" ? data.label : "思考",
              content: text,
              sequence: typeof data.sequence === "number" ? data.sequence : Date.now(),
            });
            break;
          }

          case "confirm_request":
          case "pending_suggestion": {
            appendSuggestion({
              id:
                typeof data.confirm_id === "string"
                  ? data.confirm_id
                  : typeof data.id === "string"
                    ? data.id
                    : crypto.randomUUID(),
              type: event as "confirm_request" | "pending_suggestion",
              tool: typeof data.tool === "string" ? data.tool : undefined,
              args:
                typeof data.args === "object" && data.args !== null
                  ? (data.args as Record<string, unknown>)
                  : undefined,
              summary:
                typeof data.summary === "string"
                  ? data.summary
                  : typeof data.description === "string"
                    ? data.description
                    : undefined,
              sequence: typeof data.sequence === "number" ? data.sequence : Date.now(),
            });
            break;
          }

          case "progress": {
            const msg =
              typeof data.message === "string"
                ? data.message
                : typeof data.progress === "string"
                  ? data.progress
                  : null;
            setProgress(msg);
            break;
          }

          case "task_complete":
          case "done": {
            setOrchestratorState("DONE");
            setProgress(null);
            break;
          }

          case "cancelled": {
            setOrchestratorState("CANCELLED");
            setProgress(null);
            break;
          }

          case "checkpoint":
          default: {
            // Ignore checkpoints and unknown events (or log them)
            if (process.env.NODE_ENV === "development") {
              console.log("[SSE] unhandled event:", event, data);
            }
            break;
          }
        }
      }
    },
    [
      appendMessage,
      appendToolCall,
      updateToolCallStatus,
      appendReasoning,
      appendSuggestion,
      setOrchestratorState,
      setProgress,
      setTaskId,
      setStreaming,
      updateLastAssistantMessage,
      setHandoffSummary,
    ],
  );

  const cancel = useCallback(
    async (projectId: string) => {
      abortControllerRef.current?.abort();
      setStreaming(false);
      try {
        await fetch(`/api/project/${projectId}/agent/chat/cancel`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({}),
        });
      } catch {
        /* no-op */
      }
    },
    [setStreaming],
  );

  const checkResume = useCallback(
    async (projectId: string) => {
      try {
        const tasksRes = await fetch(`/api/project/${projectId}/agent/tasks`);
        if (!tasksRes.ok) return;
        const tasksBody = (await tasksRes.json()) as {
          data?: { tasks?: Array<{ id: string; status: string }> };
        };
        const tasks = tasksBody.data?.tasks ?? [];
        const activeTask = tasks.find(
          (t) => t.status === "waiting_user" || t.status === "running",
        );
        if (activeTask) {
          setTaskId(activeTask.id);
          const pendingRes = await fetch(
            `/api/project/${projectId}/agent/pending-actions`,
          );
          if (pendingRes.ok) {
            const pendingBody = (await pendingRes.json()) as {
              data?: { task_id?: string | null; confirm_ids?: string[] };
            };
            if (pendingBody.data?.task_id) {
              setTaskId(pendingBody.data.task_id);
            }
          }
        }
      } catch {
        /* no-op */
      }
    },
    [setTaskId],
  );

  return { send, cancel, reset, checkResume };
}

/** Parse a single SSE chunk (one event block) into event + data. */
export function parseSSEChunk(chunk: string): SSEEvent | null {
  let event = "message";
  let dataStr = "";

  for (const line of chunk.split("\n")) {
    if (line.startsWith("event: ")) {
      event = line.slice(7).trim();
    } else if (line.startsWith("data: ")) {
      dataStr = line.slice(6);
    }
  }

  if (!dataStr) return null;

  try {
    const data = JSON.parse(dataStr) as Record<string, unknown>;
    return { event, data };
  } catch {
    if (process.env.NODE_ENV === "development") {
      console.warn("[SSE] unparseable data:", dataStr);
    }
    return null;
  }
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
