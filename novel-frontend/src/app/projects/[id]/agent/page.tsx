"use client";

import { useParams } from "next/navigation";
import { useState, useRef, useEffect } from "react";
import { useAgentSSE } from "@/hooks/use-sse";
import { useAgentStore } from "@/stores/agent";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Loader2, Send, RotateCcw, Bot, User } from "lucide-react";

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

  const handleReset = () => {
    reset();
  };

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <header className="flex items-center justify-between border-b px-6 py-3">
        <div>
          <h1 className="text-lg font-semibold">Agent 助手</h1>
          <p className="text-xs text-zinc-500">
            AI 写作助手 · 对话与脑暴
          </p>
        </div>
        <div className="flex items-center gap-2">
          {isStreaming && (
            <span className="flex items-center gap-1 text-xs text-blue-500">
              <Loader2 className="size-3 animate-spin" />
              响应中...
            </span>
          )}
          <Button variant="ghost" size="sm" onClick={handleReset} disabled={isStreaming}>
            <RotateCcw className="size-4" />
            新对话
          </Button>
        </div>
      </header>

      {/* Messages */}
      <ScrollArea className="flex-1 px-6 py-4">
        <div className="mx-auto max-w-3xl space-y-4">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center py-32 text-center">
              <Bot className="size-12 text-zinc-300" />
              <p className="mt-4 text-lg font-medium text-zinc-500">
                开始你的创作对话
              </p>
              <p className="mt-1 text-sm text-zinc-400">
                发送写作请求、灵感想法，或者输入 <code className="rounded bg-zinc-100 px-1 dark:bg-zinc-800">/brainstorm</code> 进入脑暴模式
              </p>
            </div>
          )}

          {messages.map((msg) => (
            <Bubble key={msg.id} msg={msg} />
          ))}

          {isStreaming && messages.length > 0 && (
            <div className="flex items-center gap-2 text-sm text-zinc-400">
              <Loader2 className="size-3 animate-spin" />
              等待响应...
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </ScrollArea>

      {/* Input */}
      <footer className="border-t px-6 py-4">
        <div className="mx-auto flex max-w-3xl gap-2">
          <Input
            placeholder={isStreaming ? "等待响应..." : "输入消息，或 /brainstorm 进入脑暴..."}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
            disabled={isStreaming}
            className="flex-1"
          />
          <Button
            onClick={handleSend}
            disabled={!input.trim() || isStreaming}
          >
            <Send className="size-4" />
          </Button>
        </div>
      </footer>
    </div>
  );
}

function Bubble({ msg }: { msg: { id: string; role: string; content: string; messageType?: string } }) {
  const isUser = msg.role === "user";
  const isSystem = msg.role === "system";

  if (isSystem) {
    return (
      <div className="flex justify-center">
        <span className="rounded bg-red-50 px-2 py-0.5 text-xs text-red-500 dark:bg-red-950">
          {msg.content}
        </span>
      </div>
    );
  }

  return (
    <div className={`flex gap-3 ${isUser ? "justify-end" : ""}`}>
      {!isUser && (
        <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-blue-100 dark:bg-blue-900">
          <Bot className="size-4 text-blue-600 dark:text-blue-300" />
        </div>
      )}
      <Card
        className={`max-w-[75%] px-4 py-2.5 ${
          isUser
            ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-black"
            : ""
        }`}
      >
        {msg.messageType && msg.messageType !== "user_message" && !isUser && (
          <span className="mb-0.5 block text-[10px] uppercase tracking-wide text-zinc-400">
            {msg.messageType}
          </span>
        )}
        <p className="whitespace-pre-wrap text-sm leading-relaxed">
          {msg.content}
        </p>
      </Card>
      {isUser && (
        <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-zinc-200 dark:bg-zinc-700">
          <User className="size-4" />
        </div>
      )}
    </div>
  );
}
