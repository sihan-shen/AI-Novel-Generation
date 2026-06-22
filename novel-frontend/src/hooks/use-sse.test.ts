import { describe, it, expect, beforeEach } from "vitest";
import { parseSSEChunk } from "./use-sse";
import {
  useAgentStore,
  type ToolCallEvent,
  type SuggestionEvent,
} from "@/stores/agent";

describe("SSE parser (parseSSEChunk)", () => {
  it("parses event: and data: lines into an SSEEvent", () => {
    const chunk = "event: text_delta\ndata: {\"content\":\"hello\"}";
    const result = parseSSEChunk(chunk);
    expect(result).not.toBeNull();
    expect(result?.event).toBe("text_delta");
    expect(result?.data).toEqual({ content: "hello" });
  });

  it("returns null when data: line is missing", () => {
    const chunk = "event: text_delta\n";
    const result = parseSSEChunk(chunk);
    expect(result).toBeNull();
  });

  it("returns null for malformed JSON in data: line", () => {
    const chunk = "event: text_delta\ndata: {broken json}";
    const result = parseSSEChunk(chunk);
    expect(result).toBeNull();
  });

  it("defaults event to 'message' when event: line is missing", () => {
    const chunk = 'data: {"content":"hi"}';
    const result = parseSSEChunk(chunk);
    expect(result?.event).toBe("message");
    expect(result?.data).toEqual({ content: "hi" });
  });
});

describe("SSE event handling → store state", () => {
  beforeEach(() => {
    useAgentStore.getState().reset();
  });

  it("text_delta event accumulates into the last assistant message", () => {
    useAgentStore.getState().updateLastAssistantMessage("Hello");
    useAgentStore.getState().updateLastAssistantMessage(" world");
    expect(useAgentStore.getState().messages).toHaveLength(1);
    expect(useAgentStore.getState().messages[0].role).toBe("assistant");
    expect(useAgentStore.getState().messages[0].content).toBe("Hello world");
  });

  it("tool_call event adds to the toolCalls slice", () => {
    const tc: ToolCallEvent = {
      id: "tc-1",
      tool: "search_settings",
      args: { q: "magic" },
      status: "running",
      sequence: 1,
    };
    useAgentStore.getState().appendToolCall(tc);
    expect(useAgentStore.getState().toolCalls).toHaveLength(1);
    expect(useAgentStore.getState().toolCalls[0].tool).toBe("search_settings");
    expect(useAgentStore.getState().toolCalls[0].status).toBe("running");
  });

  it("confirm_request event adds to the suggestions slice", () => {
    const s: SuggestionEvent = {
      id: "conf-1",
      type: "confirm_request",
      tool: "propose_setting",
      args: { name: "Magic System" },
      summary: "Add a magic system",
      sequence: 2,
    };
    useAgentStore.getState().appendSuggestion(s);
    expect(useAgentStore.getState().suggestions).toHaveLength(1);
    expect(useAgentStore.getState().suggestions[0].type).toBe("confirm_request");
    expect(useAgentStore.getState().suggestions[0].id).toBe("conf-1");
  });

  it("malformed data line is skipped without crashing the parser", () => {
    const chunk = "event: text_delta\ndata: {broken";
    const result = parseSSEChunk(chunk);
    expect(result).toBeNull();
  });

  it("full synthetic SSE transcript populates store correctly", () => {
    // Simulate parsing and handling multiple events from a synthetic stream
    const events: Array<{ event: string; data: Record<string, unknown> }> = [
      { event: "agent_start", data: { task_id: "task-1", state: "WRITING" } },
      { event: "text_delta", data: { content: "Once" } },
      { event: "text_delta", data: { content: " upon" } },
      {
        event: "tool_call",
        data: {
          tool_call_id: "tc-1",
          tool: "get_outline",
          args: {},
          sequence: 3,
        },
      },
      {
        event: "tool_result",
        data: {
          tool_call_id: "tc-1",
          success: true,
          content: "Outline data",
        },
      },
      {
        event: "confirm_request",
        data: {
          confirm_id: "conf-1",
          tool: "propose_setting",
          summary: "Add magic",
          sequence: 5,
        },
      },
      { event: "done", data: {} },
    ];

    for (const e of events) {
      const store = useAgentStore.getState();
      switch (e.event) {
        case "agent_start": {
          store.setTaskId(
            typeof e.data.task_id === "string" ? e.data.task_id : null,
          );
          store.setOrchestratorState(
            typeof e.data.state === "string" ? e.data.state : "IDLE",
          );
          break;
        }
        case "text_delta": {
          const text =
            typeof e.data.content === "string"
              ? e.data.content
              : typeof e.data.text === "string"
                ? e.data.text
                : "";
          if (text) store.updateLastAssistantMessage(text);
          break;
        }
        case "tool_call": {
          store.appendToolCall({
            id:
              typeof e.data.tool_call_id === "string"
                ? e.data.tool_call_id
                : "tc-unknown",
            tool: typeof e.data.tool === "string" ? e.data.tool : "unknown",
            args:
              typeof e.data.args === "object" && e.data.args !== null
                ? (e.data.args as Record<string, unknown>)
                : {},
            status: "running",
            sequence:
              typeof e.data.sequence === "number" ? e.data.sequence : 0,
          });
          break;
        }
        case "tool_result": {
          const tcId =
            typeof e.data.tool_call_id === "string"
              ? e.data.tool_call_id
              : "";
          const success = e.data.success === true;
          if (tcId) {
            store.updateToolCallStatus(
              tcId,
              success ? "success" : "failed",
              typeof e.data.content === "string"
                ? e.data.content
                : undefined,
            );
          }
          break;
        }
        case "confirm_request": {
          store.appendSuggestion({
            id:
              typeof e.data.confirm_id === "string"
                ? e.data.confirm_id
                : "conf-unknown",
            type: "confirm_request",
            tool:
              typeof e.data.tool === "string" ? e.data.tool : undefined,
            args:
              typeof e.data.args === "object" && e.data.args !== null
                ? (e.data.args as Record<string, unknown>)
                : undefined,
            summary:
              typeof e.data.summary === "string"
                ? e.data.summary
                : undefined,
            sequence:
              typeof e.data.sequence === "number" ? e.data.sequence : 0,
          });
          break;
        }
        case "done": {
          store.setOrchestratorState("DONE");
          break;
        }
      }
    }

    expect(useAgentStore.getState().taskId).toBe("task-1");
    expect(useAgentStore.getState().orchestratorState).toBe("DONE");
    expect(useAgentStore.getState().messages).toHaveLength(1);
    expect(useAgentStore.getState().messages[0].content).toBe("Once upon");
    expect(useAgentStore.getState().toolCalls).toHaveLength(1);
    expect(useAgentStore.getState().toolCalls[0].tool).toBe("get_outline");
    expect(useAgentStore.getState().toolCalls[0].status).toBe("success");
    expect(useAgentStore.getState().suggestions).toHaveLength(1);
    expect(useAgentStore.getState().suggestions[0].type).toBe("confirm_request");
  });
});
