"use client";

import { useParams } from "next/navigation";
import { useState, useRef, useEffect } from "react";
import { useAgentSSE } from "@/hooks/use-sse";
import { useAgentStore } from "@/stores/agent";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Loader2, Send, RotateCcw, Bot, User, Sparkles } from "lucide-react";

export default function AgentPage() {
  const { id: projectId } = useParams<{ id: string }>();
  const { send, reset } = useAgentSSE();
  const { messages, isStreaming } = useAgentStore();
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = () => {
    if (!input.trim() || isStreaming) return;
    send(projectId, input.trim());
    setInput("");
  };

  const handleReset = () => reset();

  return (
    <div className="flex h-full flex-col" style={{ background: "var(--surface-page)" }}>
      {/* Header */}
      <header
        className="flex items-center justify-between px-6 py-3 border-b shrink-0"
        style={{ borderColor: "var(--border-subtle)", background: "var(--surface-sidebar)" }}
      >
        <div className="flex items-center gap-3">
          <div
            className="size-8 rounded-lg flex items-center justify-center"
            style={{ background: "var(--gradient-accent)" }}
          >
            <Bot className="size-4 text-white" />
          </div>
          <div>
            <h1 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
              Agent 助手
            </h1>
            <p className="text-xs" style={{ color: "var(--text-tertiary)" }}>
              AI 写作助手 · 对话与脑暴
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {isStreaming && (
            <span className="flex items-center gap-1 text-xs" style={{ color: "var(--accent-text)" }}>
              <Loader2 className="size-3 animate-spin" />
              响应中
            </span>
          )}
          <Button variant="ghost" size="sm" onClick={handleReset} disabled={isStreaming}>
            <RotateCcw className="size-4 mr-1" />
            新对话
          </Button>
        </div>
      </header>

      {/* Messages */}
      <ScrollArea className="flex-1 px-6 py-4">
        <div className="mx-auto space-y-4" style={{ maxWidth: "var(--layout-chat-max-width)" }}>
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center py-32 text-center">
              <div
                className="size-16 rounded-full flex items-center justify-center mb-4"
                style={{
                  background: "var(--gradient-accent)",
                  boxShadow: "0 0 24px var(--accent-glow)",
                }}
              >
                <Sparkles className="size-7 text-white" />
              </div>
              <p className="text-lg font-medium" style={{ color: "var(--text-primary)" }}>
                开始你的创作对话
              </p>
              <p className="mt-1 text-sm" style={{ color: "var(--text-tertiary)" }}>
                发送写作请求、灵感想法，或输入
                <code
                  className="mx-1 rounded px-1 py-0.5 text-xs"
                  style={{
                    background: "var(--bg-elevated)",
                    color: "var(--accent-text)",
                  }}
                >
                  /brainstorm
                </code>
                进入脑暴模式
              </p>
            </div>
          )}

          {messages.map((msg) => (
            <ChatBubble key={msg.id} msg={msg} />
          ))}

          {isStreaming && messages.length > 0 && (
            <div className="flex items-center gap-2 text-sm" style={{ color: "var(--accent-text)" }}>
              <div className="flex gap-1">
                <span className="size-1.5 rounded-full animate-bounce" style={{ background: "var(--accent-base)" }} />
                <span className="size-1.5 rounded-full animate-bounce" style={{ background: "var(--accent-base)", animationDelay: "0.2s" }} />
                <span className="size-1.5 rounded-full animate-bounce" style={{ background: "var(--accent-base)", animationDelay: "0.4s" }} />
              </div>
              等待响应...
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </ScrollArea>

      {/* Input */}
      <footer
        className="px-6 py-4 border-t shrink-0"
        style={{ borderColor: "var(--border-subtle)", background: "var(--surface-page)" }}
      >
        <div className="mx-auto flex gap-2" style={{ maxWidth: "var(--layout-chat-max-width)" }}>
          <div
            className="flex-1 flex items-center gap-2 rounded-xl px-3"
            style={{
              background: "var(--input-bg)",
              border: "1px solid var(--input-border)",
            }}
          >
            <Sparkles className="size-4 shrink-0" style={{ color: "var(--text-muted)" }} />
            <Input
              placeholder={isStreaming ? "等待响应..." : "输入消息，或 /brainstorm 进入脑暴..."}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
              disabled={isStreaming}
              className="border-0 focus-visible:ring-0 !shadow-none px-0"
              style={{ background: "transparent" }}
            />
          </div>
          <Button onClick={handleSend} disabled={!input.trim() || isStreaming}>
            <Send className="size-4" />
          </Button>
        </div>
      </footer>
    </div>
  );
}

/* ────────── Chat Bubble ────────── */

interface ChatMessage {
  id: string;
  role: string;
  content: string;
  messageType?: string;
  status?: string;
  label?: string;
}

function ChatBubble({ msg }: { msg: ChatMessage }) {
  const isUser = msg.role === "user";
  const isSystem = msg.role === "system";
  const isToolCall = msg.messageType === "tool_call";
  const isReasoning = msg.messageType === "reasoning";
  const [reasoningOpen, setReasoningOpen] = useState(false);

  if (isSystem) {
    return (
      <div className="flex justify-center">
        <span
          className="rounded-full px-2 py-0.5 text-xs"
          style={{ background: "var(--danger-subtle)", color: "var(--danger-text)" }}
        >
          {msg.content}
        </span>
      </div>
    );
  }

  if (isToolCall) {
    const statusIcon =
      msg.status === "running" ? "🔄" :
      msg.status === "success" ? "✓" :
      msg.status === "failed" ? "✗" :
      msg.status === "cancelled" ? "—" : "⏳";
    const statusColor =
      msg.status === "running" ? "var(--processing-text)" :
      msg.status === "success" ? "var(--success-text)" :
      msg.status === "failed" ? "var(--danger-text)" : "var(--text-muted)";

    return (
      <div className="flex justify-start">
        <div
          className="rounded-lg px-4 py-2.5 text-sm max-w-[75%]"
          style={{
            background: "var(--processing-subtle)",
            border: "1px solid var(--processing-border)",
          }}
        >
          <span className="mr-1" style={{ color: statusColor }}>{statusIcon}</span>
          <span style={{ color: "var(--text-secondary)" }}>{msg.content}</span>
        </div>
      </div>
    );
  }

  if (isReasoning) {
    const label = (msg.label || "分析信息").slice(0, 32);
    return (
      <div className="flex justify-start">
        <div className="max-w-[75%]">
          <button
            onClick={() => setReasoningOpen(!reasoningOpen)}
            className="flex items-center gap-2 rounded-full px-3 py-1 text-xs transition-colors"
            style={{
              background: "var(--accent-subtle)",
              color: "var(--accent-text)",
            }}
          >
            <span>{reasoningOpen ? "▼" : "▶"}</span>
            <span className="truncate max-w-[32ch]">{label}</span>
          </button>
          {reasoningOpen && (
            <div
              className="mt-2 rounded-lg px-4 py-3 text-sm italic leading-relaxed"
              style={{
                background: "var(--accent-subtle)",
                color: "var(--text-tertiary)",
                borderLeft: "2px solid var(--accent-border)",
              }}
            >
              {msg.content}
            </div>
          )}
        </div>
      </div>
    );
  }

  // User or assistant message
  return (
    <div className={`flex gap-3 ${isUser ? "justify-end" : ""}`}>
      {!isUser && (
        <div
          className="size-8 shrink-0 rounded-full flex items-center justify-center"
          style={{ background: "var(--gradient-accent)" }}
        >
          <Bot className="size-4 text-white" />
        </div>
      )}

      <div
        className={`max-w-[75%] rounded-xl px-4 py-2.5 ${isUser ? "" : "backdrop-blur-[6px]"}`}
        style={{
          background: isUser ? "var(--bubble-user-bg)" : "var(--surface-glass-bg)",
          color: isUser ? "var(--bubble-user-text)" : "var(--text-secondary)",
          border: isUser ? "none" : "1px solid var(--surface-glass-border)",
        }}
      >
        {msg.messageType && msg.messageType !== "user_message" && !isUser && (
          <span
            className="mb-1 block text-[0.6rem] uppercase tracking-wide"
            style={{ color: "var(--text-muted)" }}
          >
            {msg.messageType}
          </span>
        )}
        <p className="whitespace-pre-wrap text-sm leading-relaxed">
          {msg.content}
        </p>
      </div>

      {isUser && (
        <div
          className="size-8 shrink-0 rounded-full flex items-center justify-center"
          style={{
            background: "var(--bg-elevated-hover)",
            border: "1px solid var(--border-subtle)",
          }}
        >
          <User className="size-4" style={{ color: "var(--text-tertiary)" }} />
        </div>
      )}
    </div>
  );
}
