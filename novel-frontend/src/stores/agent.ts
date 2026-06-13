import { create } from "zustand";

export interface AgentMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  messageType?: string;
  sequence: number;
}

interface AgentStore {
  messages: AgentMessage[];
  isConnected: boolean;
  taskId: string | null;
  isStreaming: boolean;

  appendMessage: (msg: AgentMessage) => void;
  updateLastMessage: (content: string) => void;
  setConnected: (v: boolean) => void;
  setTaskId: (id: string | null) => void;
  setStreaming: (v: boolean) => void;
  reset: () => void;
}

export const useAgentStore = create<AgentStore>((set) => ({
  messages: [],
  isConnected: false,
  taskId: null,
  isStreaming: false,

  appendMessage: (msg) =>
    set((state) => ({ messages: [...state.messages, msg] })),

  updateLastMessage: (content) =>
    set((state) => {
      const msgs = [...state.messages];
      const last = msgs[msgs.length - 1];
      if (last && last.role === "assistant") {
        msgs[msgs.length - 1] = { ...last, content: last.content + content };
      }
      return { messages: msgs };
    }),

  setConnected: (v) => set({ isConnected: v }),
  setTaskId: (id) => set({ taskId: id }),
  setStreaming: (v) => set({ isStreaming: v }),
  reset: () =>
    set({ messages: [], isConnected: false, taskId: null, isStreaming: false }),
}));
