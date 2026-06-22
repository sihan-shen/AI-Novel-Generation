"use client";

import { useCallback, useRef } from "react";
import {
  useAgentStore,
  type ChatRequest,
  type AgentMessage,
  type ToolCallEvent,
  type ReasoningEvent,
  type SuggestionEvent,
} from "@/stores/agent";

interface SSEEvent {
  event: string;
  data: Record<string, unknown>;
}

/** Subset of AgentStore actions needed by SSE event handlers. */
export interface AgentStoreActions {
  appendMessage: (msg: AgentMessage) => void;
  appendToolCall: (tc: ToolCallEvent) => void;
  updateToolCallStatus: (id: string, status: ToolCallEvent["status"], result?: string) => void;
  appendReasoning: (r: ReasoningEvent) => void;
  appendSuggestion: (s: SuggestionEvent) => void;
  setOrchestratorState: (state: string | null) => void;
  setProgress: (p: string | null) => void;
  setTaskId: (id: string | null) => void;
  updateLastAssistantMessage: (chunk: string) => void;
  setHandoffSummary: (summary: string | null) => void;
}

export type EventHandler = (data: Record<string, unknown>, store: AgentStoreActions) => void;

// ── Handler implementations ───────────────────────────────────────

const handleAgentStart: EventHandler = (data, store) => {
  const tid = typeof data.task_id === "string" ? data.task_id : null;
  store.setTaskId(tid);
  const state = typeof data.state === "string" ? data.state : "IDLE";
  store.setOrchestratorState(state);
};

const handleTextDelta: EventHandler = (data, store) => {
  const text =
    typeof data.content === "string"
      ? data.content
      : typeof data.text === "string"
        ? data.text
        : "";
  if (text) {
    store.updateLastAssistantMessage(text);
  }
};

const handleAgentOutput: EventHandler = (data, store) => {
  const text = extractContent(data);
  store.appendMessage({
    id: crypto.randomUUID(),
    role: "assistant",
    content: text,
    sequence: typeof data.sequence === "number" ? data.sequence : Date.now(),
  });
  const summary = typeof data.summary === "string" ? data.summary : text;
  store.setHandoffSummary(summary);
};

const handleToolCall: EventHandler = (data, store) => {
  const tcId =
    typeof data.tool_call_id === "string"
      ? data.tool_call_id
      : crypto.randomUUID();
  store.appendToolCall({
    id: tcId,
    tool: typeof data.tool === "string" ? data.tool : "unknown",
    args:
      typeof data.args === "object" && data.args !== null
        ? (data.args as Record<string, unknown>)
        : {},
    status: "running",
    sequence: typeof data.sequence === "number" ? data.sequence : Date.now(),
  });
};

const handleToolResult: EventHandler = (data, store) => {
  const tcId =
    typeof data.tool_call_id === "string" ? data.tool_call_id : "";
  const success = data.success === true;
  const resultText = extractContent(data);
  if (tcId) {
    store.updateToolCallStatus(
      tcId,
      success ? "success" : "failed",
      resultText,
    );
  }
};

const handleOrchestratorThought: EventHandler = (data, store) => {
  const text =
    typeof data.text === "string" ? data.text : extractContent(data);
  store.appendReasoning({
    id: crypto.randomUUID(),
    label: typeof data.label === "string" ? data.label : "思考",
    content: text,
    sequence: typeof data.sequence === "number" ? data.sequence : Date.now(),
  });
};

const handleSuggestion: EventHandler = (data, store) => {
  store.appendSuggestion({
    id:
      typeof data.confirm_id === "string"
        ? data.confirm_id
        : typeof data.id === "string"
          ? data.id
          : crypto.randomUUID(),
    type: "confirm_request" as const,
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
};

const handleProgress: EventHandler = (data, store) => {
  const msg =
    typeof data.message === "string"
      ? data.message
      : typeof data.progress === "string"
        ? data.progress
        : null;
  store.setProgress(msg);
};

const handleDone: EventHandler = (_data, store) => {
  store.setOrchestratorState("DONE");
  store.setProgress(null);
};

const handleCancelled: EventHandler = (_data, store) => {
  store.setOrchestratorState("CANCELLED");
  store.setProgress(null);
};

// ── Handler registry ──────────────────────────────────────────────

export const eventHandlers: Record<string, EventHandler> = {
  agent_start: handleAgentStart,
  text_delta: handleTextDelta,
  agent_output: handleAgentOutput,
  brainstorm_response: handleAgentOutput,
  brainstorm_end: handleAgentOutput,
  brainstorm_handoff: handleAgentOutput,
  tool_call: handleToolCall,
  tool_result: handleToolResult,
  orchestrator_thought: handleOrchestratorThought,
  confirm_request: handleSuggestion,
  pending_suggestion: handleSuggestion,
  progress: handleProgress,
  task_complete: handleDone,
  done: handleDone,
  cancelled: handleCancelled,
};

/** Process a single SSE event against the store. */
export function handleSSEEvent(
  event: SSEEvent,
  store: AgentStoreActions,
): void {
  const handler = eventHandlers[event.event];
  if (handler) {
    handler(event.data, store);
  } else if (process.env.NODE_ENV === "development") {
    console.log("[SSE] unhandled event:", event.event, event.data);
  }
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

      const storeActions: AgentStoreActions = {
        appendMessage,
        appendToolCall,
        updateToolCallStatus,
        appendReasoning,
        appendSuggestion,
        setOrchestratorState,
        setProgress,
        setTaskId,
        updateLastAssistantMessage,
        setHandoffSummary,
      };

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
            handleSSEEvent(sseEvent, storeActions);
          }
        }

        // Process any remaining data in the buffer
        if (buffer.trim()) {
          const sseEvent = parseSSEChunk(buffer);
          if (sseEvent) {
            handleSSEEvent(sseEvent, storeActions);
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
