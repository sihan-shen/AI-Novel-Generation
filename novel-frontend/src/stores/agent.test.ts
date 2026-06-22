import { describe, it, expect, beforeEach } from "vitest";
import {
  useAgentStore,
  type AgentMessage,
  type ToolCallEvent,
  type SuggestionEvent,
} from "./agent";

describe("Agent store reducer", () => {
  beforeEach(() => {
    useAgentStore.getState().reset();
  });

  it("appendMessage adds a message to the messages array", () => {
    const msg: AgentMessage = {
      id: "msg-1",
      role: "user",
      content: "Hello",
      sequence: 1,
    };
    useAgentStore.getState().appendMessage(msg);
    expect(useAgentStore.getState().messages).toHaveLength(1);
    expect(useAgentStore.getState().messages[0]).toEqual(msg);
  });

  it("updateLastAssistantMessage appends chunk to the last assistant message", () => {
    useAgentStore.getState().appendMessage({
      id: "msg-1",
      role: "assistant",
      content: "Hello",
      sequence: 1,
    });
    useAgentStore.getState().updateLastAssistantMessage(" world");
    const last = useAgentStore.getState().messages.at(-1);
    expect(last?.content).toBe("Hello world");
    expect(last?.role).toBe("assistant");
  });

  it("updateLastAssistantMessage creates a new assistant message when none exists", () => {
    useAgentStore.getState().updateLastAssistantMessage("First chunk");
    expect(useAgentStore.getState().messages).toHaveLength(1);
    expect(useAgentStore.getState().messages[0].role).toBe("assistant");
    expect(useAgentStore.getState().messages[0].content).toBe("First chunk");
  });

  it("appendToolCall adds a tool call to the toolCalls array", () => {
    const tc: ToolCallEvent = {
      id: "tc-1",
      tool: "search_settings",
      args: { q: "magic" },
      status: "running",
      sequence: 2,
    };
    useAgentStore.getState().appendToolCall(tc);
    expect(useAgentStore.getState().toolCalls).toHaveLength(1);
    expect(useAgentStore.getState().toolCalls[0]).toEqual(tc);
  });

  it("appendSuggestion adds a suggestion to the suggestions array", () => {
    const s: SuggestionEvent = {
      id: "sug-1",
      type: "pending_suggestion",
      tool: "propose_setting",
      summary: "Add magic system",
      sequence: 3,
    };
    useAgentStore.getState().appendSuggestion(s);
    expect(useAgentStore.getState().suggestions).toHaveLength(1);
    expect(useAgentStore.getState().suggestions[0]).toEqual(s);
  });

  it("removeSuggestion removes a suggestion by id", () => {
    const store = useAgentStore.getState();
    store.appendSuggestion({
      id: "sug-1",
      type: "pending_suggestion",
      sequence: 1,
    });
    store.appendSuggestion({
      id: "sug-2",
      type: "confirm_request",
      sequence: 2,
    });
    store.removeSuggestion("sug-1");
    expect(useAgentStore.getState().suggestions).toHaveLength(1);
    expect(useAgentStore.getState().suggestions[0].id).toBe("sug-2");
  });

  it("setOrchestratorState updates the orchestrator state", () => {
    useAgentStore.getState().setOrchestratorState("WRITING");
    expect(useAgentStore.getState().orchestratorState).toBe("WRITING");
  });

  it("reset clears all store slices", () => {
    const store = useAgentStore.getState();
    store.appendMessage({
      id: "m1",
      role: "user",
      content: "x",
      sequence: 1,
    });
    store.appendToolCall({
      id: "tc1",
      tool: "t",
      args: {},
      status: "running",
      sequence: 2,
    });
    store.appendSuggestion({
      id: "s1",
      type: "pending_suggestion",
      sequence: 3,
    });
    store.setOrchestratorState("REVIEWING");
    store.setProgress("50%");
    store.setTaskId("task-1");
    store.setHandoffSummary("summary");
    store.setStreaming(true);

    store.reset();

    expect(useAgentStore.getState().messages).toHaveLength(0);
    expect(useAgentStore.getState().toolCalls).toHaveLength(0);
    expect(useAgentStore.getState().suggestions).toHaveLength(0);
    expect(useAgentStore.getState().reasoning).toHaveLength(0);
    expect(useAgentStore.getState().orchestratorState).toBeNull();
    expect(useAgentStore.getState().progress).toBeNull();
    expect(useAgentStore.getState().taskId).toBeNull();
    expect(useAgentStore.getState().handoffSummary).toBeNull();
    expect(useAgentStore.getState().isStreaming).toBe(false);
  });
});
