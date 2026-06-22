"use client";

import { Bot, User } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { AgentMessage } from "@/stores/agent";

export function ChatBubble({ msg }: { msg: AgentMessage }) {
  const isUser = msg.role === "user";
  const isSystem = msg.role === "system";

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

  return (
    <div
      className={`flex gap-3 ${isUser ? "justify-end" : ""}`}
      aria-label={isUser ? "用户消息" : "助手消息"}
    >
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
        {isUser ? (
          <p className="whitespace-pre-wrap text-sm leading-relaxed">
            {msg.content}
          </p>
        ) : (
          <div className="text-sm leading-relaxed">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
          </div>
        )}
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
