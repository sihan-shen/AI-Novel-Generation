import { create } from "zustand";

export interface AgentMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  sequence: number;
}

export interface ToolCallEvent {
  id: string;
  tool: string;
  args: Record<string, unknown>;
  status: "running" | "success" | "failed" | "cancelled";
  result?: string;
  sequence: number;
}

export interface ReasoningEvent {
  id: string;
  label: string;
  content: string;
  sequence: number;
}

export interface SuggestionEvent {
  id: string;
  type: "confirm_request" | "pending_suggestion";
  tool?: string;
  args?: Record<string, unknown>;
  summary?: string;
  sequence: number;
}

export interface ChatRequest {
  message: string;
  chapter_outline_id?: string | null;
  target_words?: number | null;
  mode?: string | null;
  autonomy_config?: Record<string, unknown> | null;
}

interface AgentStore {
  messages: AgentMessage[];
  toolCalls: ToolCallEvent[];
  reasoning: ReasoningEvent[];
  suggestions: SuggestionEvent[];
  orchestratorState: string | null;
  progress: string | null;
  taskId: string | null;
  isStreaming: boolean;
  handoffSummary: string | null;

  appendMessage: (msg: AgentMessage) => void;
  appendToolCall: (tc: ToolCallEvent) => void;
  updateToolCallStatus: (id: string, status: ToolCallEvent["status"], result?: string) => void;
  appendReasoning: (r: ReasoningEvent) => void;
  appendSuggestion: (s: SuggestionEvent) => void;
  removeSuggestion: (id: string) => void;
  setOrchestratorState: (state: string | null) => void;
  setProgress: (p: string | null) => void;
  setTaskId: (id: string | null) => void;
  setStreaming: (v: boolean) => void;
  updateLastAssistantMessage: (chunk: string) => void;
  setHandoffSummary: (summary: string | null) => void;
  reset: () => void;
}

export const useAgentStore = create<AgentStore>((set) => ({
  messages: [],
  toolCalls: [],
  reasoning: [],
  suggestions: [],
  orchestratorState: null,
  progress: null,
  taskId: null,
  isStreaming: false,
  handoffSummary: null,

  appendMessage: (msg) =>
    set((state) => ({ messages: [...state.messages, msg] })),

  appendToolCall: (tc) =>
    set((state) => ({ toolCalls: [...state.toolCalls, tc] })),

  updateToolCallStatus: (id, status, result) =>
    set((state) => ({
      toolCalls: state.toolCalls.map((tc) =>
        tc.id === id ? { ...tc, status, ...(result !== undefined ? { result } : {}) } : tc
      ),
    })),

  appendReasoning: (r) =>
    set((state) => ({ reasoning: [...state.reasoning, r] })),

  appendSuggestion: (s) =>
    set((state) => ({ suggestions: [...state.suggestions, s] })),
  removeSuggestion: (id) =>
    set((state) => ({
      suggestions: state.suggestions.filter((s) => s.id !== id),
    })),

  setOrchestratorState: (state) => set({ orchestratorState: state }),
  setProgress: (p) => set({ progress: p }),
  setTaskId: (id) => set({ taskId: id }),
  setStreaming: (v) => set({ isStreaming: v }),
  setHandoffSummary: (summary) => set({ handoffSummary: summary }),

  updateLastAssistantMessage: (chunk) =>
    set((state) => {
      const msgs = state.messages;
      if (msgs.length === 0 || msgs[msgs.length - 1].role !== "assistant") {
        return {
          messages: [
            ...msgs,
            {
              id: crypto.randomUUID(),
              role: "assistant",
              content: chunk,
              sequence: Date.now(),
            },
          ],
        };
      }
      const last = msgs[msgs.length - 1];
      const updated: AgentMessage = { ...last, content: last.content + chunk };
      return { messages: [...msgs.slice(0, -1), updated] };
    }),

  reset: () =>
    set({
      messages: [],
      toolCalls: [],
      reasoning: [],
      suggestions: [],
      orchestratorState: null,
      progress: null,
      taskId: null,
      isStreaming: false,
      handoffSummary: null,
    }),
}));
