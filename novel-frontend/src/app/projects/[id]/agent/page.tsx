"use client";

import { useParams, useSearchParams } from "next/navigation";
import { useState, useRef, useEffect, useMemo } from "react";
import { useAgentSSE } from "@/hooks/use-sse";
import { useAgentStore } from "@/stores/agent";
import { useChapters } from "@/lib/queries/chapters";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { DropdownMenu, DropdownMenuContent, DropdownMenuLabel, DropdownMenuRadioGroup, DropdownMenuRadioItem, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Loader2, Send, RotateCcw, Bot, Sparkles, Square, Settings2 } from "lucide-react";
import { ChatBubble } from "@/components/features/agent/chat-bubble";
import { ReasoningPanel } from "@/components/features/agent/reasoning-panel";
import { ToolCallPanel } from "@/components/features/agent/tool-call-panel";
import { SuggestionCard } from "@/components/features/agent/suggestion-card";
import { TaskHistoryPanel } from "@/components/features/agent/task-history-panel";

type Mode = "auto" | "brainstorm" | "writing";
type WriteMode = "suggest" | "draft" | "direct";
type MilestoneGranularity = "chapter" | "volume" | "act";

export default function AgentPage() {
  const { id: projectId } = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const { send, cancel, reset, checkResume } = useAgentSSE();
  const {
    messages,
    toolCalls,
    reasoning,
    suggestions,
    orchestratorState,
    progress,
    isStreaming,
    handoffSummary,
  } = useAgentStore();
  const { data: chapters } = useChapters(projectId);
  const [input, setInput] = useState("");
  const initialMode = useMemo<Mode>(() => {
    const modeParam = searchParams.get("mode");
    return modeParam === "brainstorm" || modeParam === "writing" ? modeParam : "auto";
  }, [searchParams]);
  const [mode, setMode] = useState<Mode>(initialMode);
  const initialChapterId = useMemo<string | null>(() => searchParams.get("chapter"), [searchParams]);
  const [chapterId, setChapterId] = useState<string | null>(initialChapterId);
  const [writeMode, setWriteMode] = useState<WriteMode>("draft");
  const [maxRewriteRounds, setMaxRewriteRounds] = useState(3);
  const [milestoneGranularity, setMilestoneGranularity] = useState<MilestoneGranularity>("chapter");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, toolCalls, reasoning, suggestions]);
  useEffect(() => { if (projectId) checkResume(projectId); }, [projectId, checkResume]);

  const handleSend = () => {
    if (!input.trim() || isStreaming) return;
    send(projectId, {
      message: input.trim(),
      chapter_outline_id: mode === "writing" ? chapterId : null,
      target_words: 3000,
      mode: mode === "auto" ? null : mode,
      autonomy_config: {
        write_mode: writeMode,
        max_rewrite_rounds: maxRewriteRounds,
        milestone_granularity: milestoneGranularity,
      },
    });
    setInput("");
  };

  const timeline = useMemo(() => {
    const items = [
      ...messages.map((m) => ({ type: "msg" as const, seq: m.sequence, data: m })),
      ...toolCalls.map((t) => ({ type: "tool" as const, seq: t.sequence, data: t })),
      ...reasoning.map((r) => ({ type: "reasoning" as const, seq: r.sequence, data: r })),
      ...suggestions.map((s) => ({ type: "suggestion" as const, seq: s.sequence, data: s })),
    ];
    items.sort((a, b) => a.seq - b.seq);
    return items;
  }, [messages, toolCalls, reasoning, suggestions]);

  const isEmpty = messages.length === 0 && toolCalls.length === 0 && reasoning.length === 0 && suggestions.length === 0;

  const chapterPlaceholder = chapters?.length ? "选择章节" : "（暂无章节）";
  const chapterDisabled = mode === "brainstorm" || !chapters?.length;

  return (
    <div className="flex h-full flex-col" style={{ background: "var(--surface-page)" }}>
      <header className="flex items-center justify-between px-6 py-3 border-b shrink-0" style={{ borderColor: "var(--border-subtle)", background: "var(--surface-sidebar)" }}>
        <div className="flex items-center gap-3">
          <div className="size-8 rounded-lg flex items-center justify-center" style={{ background: "var(--gradient-accent)" }}>
            <Bot className="size-4 text-white" />
          </div>
          <div>
            <h1 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>Agent 助手</h1>
            <p className="text-xs" style={{ color: "var(--text-tertiary)" }}>AI 写作助手 · 对话与脑暴</p>
          </div>
          {orchestratorState && <span className="rounded-full px-2 py-0.5 text-[0.65rem] uppercase tracking-wide" style={{ background: "var(--accent-subtle)", color: "var(--accent-text)" }}>{orchestratorState}</span>}
        </div>
        <div className="flex items-center gap-2">
          {isStreaming && (
            <>
              <span className="flex items-center gap-1 text-xs" style={{ color: "var(--accent-text)" }}><Loader2 className="size-3 animate-spin" /> 响应中</span>
              <Button aria-label="停止" variant="ghost" size="sm" onClick={() => cancel(projectId)} disabled={!isStreaming} className="text-red-500 hover:text-red-600 hover:bg-red-50"><Square className="size-4 mr-1 fill-current" /> 停止</Button>
            </>
          )}
          {orchestratorState && (
            <span
              className="rounded-md px-2 py-0.5 text-xs"
              style={{ background: "var(--bg-elevated)", color: "var(--text-secondary)" }}
              data-testid="orchestrator-state-badge"
            >
              状态: {orchestratorState}
            </span>
          )}
          {handoffSummary && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                setMode("writing");
                setInput(`基于脑暴结果继续写作：\n${handoffSummary}`);
              }}
              disabled={isStreaming}
            >
              <Sparkles className="size-4 mr-1" /> 继续写作
            </Button>
          )}
          <Button variant="ghost" size="sm" onClick={reset} disabled={isStreaming}><RotateCcw className="size-4 mr-1" /> 新对话</Button>
        </div>
      </header>

      {progress && (
        <div
          className="px-6 py-1.5 text-xs border-b shrink-0"
          style={{
            background: "var(--surface-sidebar)",
            color: "var(--text-muted)",
            borderColor: "var(--border-subtle)",
          }}
          data-testid="progress-indicator"
        >
          {progress}
        </div>
      )}

      <div className="flex items-center gap-2 px-6 py-2 border-b shrink-0" style={{ borderColor: "var(--border-subtle)", background: "var(--surface-sidebar)" }}>
        <Select value={mode} onValueChange={(v) => setMode(v as Mode)}>
          <SelectTrigger className="h-7 text-xs w-24"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="auto">自动</SelectItem>
            <SelectItem value="brainstorm">脑暴</SelectItem>
            <SelectItem value="writing">写作</SelectItem>
          </SelectContent>
        </Select>

        <Select value={chapterId ?? ""} onValueChange={setChapterId} disabled={chapterDisabled}>
          <SelectTrigger className="h-7 text-xs w-40"><SelectValue placeholder={chapterPlaceholder} /></SelectTrigger>
          <SelectContent>
            {chapters?.map((c) => <SelectItem key={c.id} value={c.id}>{c.title}</SelectItem>)}
          </SelectContent>
        </Select>

        <DropdownMenu>
          <DropdownMenuTrigger className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50">
            <Settings2 className="size-3.5" />设置
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="w-44">
            <DropdownMenuLabel>写作模式</DropdownMenuLabel>
            <DropdownMenuRadioGroup value={writeMode} onValueChange={(v) => setWriteMode(v as WriteMode)}>
              <DropdownMenuRadioItem value="suggest">建议</DropdownMenuRadioItem>
              <DropdownMenuRadioItem value="draft">草稿</DropdownMenuRadioItem>
              <DropdownMenuRadioItem value="direct">直接</DropdownMenuRadioItem>
            </DropdownMenuRadioGroup>
            <DropdownMenuSeparator />
            <DropdownMenuLabel>重写轮数</DropdownMenuLabel>
            <div className="px-2 py-1 flex items-center gap-2">
              <input type="range" min={1} max={5} value={maxRewriteRounds} onChange={(e) => setMaxRewriteRounds(Number(e.target.value))} className="w-full h-1 accent-accent" />
              <span className="text-xs w-4">{maxRewriteRounds}</span>
            </div>
            <DropdownMenuSeparator />
            <DropdownMenuLabel>粒度</DropdownMenuLabel>
            <DropdownMenuRadioGroup value={milestoneGranularity} onValueChange={(v) => setMilestoneGranularity(v as MilestoneGranularity)}>
              <DropdownMenuRadioItem value="chapter">章</DropdownMenuRadioItem>
              <DropdownMenuRadioItem value="volume">卷</DropdownMenuRadioItem>
              <DropdownMenuRadioItem value="act">幕</DropdownMenuRadioItem>
            </DropdownMenuRadioGroup>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <ScrollArea className="flex-1 px-6 py-4" aria-live="polite" aria-label="消息列表">
        <div className="mx-auto space-y-4" style={{ maxWidth: "var(--layout-chat-max-width)" }}>
          {isEmpty && (
            <div className="flex flex-col items-center justify-center py-32 text-center">
              <div className="size-16 rounded-full flex items-center justify-center mb-4" style={{ background: "var(--gradient-accent)", boxShadow: "0 0 24px var(--accent-glow)" }}>
                <Sparkles className="size-7 text-white" />
              </div>
              <p className="text-lg font-medium" style={{ color: "var(--text-primary)" }}>开始你的创作对话</p>
              <p className="mt-1 text-sm" style={{ color: "var(--text-tertiary)" }}>
                发送写作请求、灵感想法，或输入 <code className="mx-1 rounded px-1 py-0.5 text-xs" style={{ background: "var(--bg-elevated)", color: "var(--accent-text)" }}>/brainstorm</code> 进入脑暴模式
              </p>
            </div>
          )}

          {timeline.map((item) => {
            switch (item.type) {
              case "msg": return <ChatBubble key={`msg-${item.data.id}`} msg={item.data} />;
              case "tool": return <ToolCallPanel key={`tool-${item.data.id}`} toolCall={item.data} />;
              case "reasoning": return <ReasoningPanel key={`r-${item.data.id}`} reasoning={item.data} />;
              case "suggestion": return <SuggestionCard key={`s-${item.data.id}`} suggestion={item.data} projectId={projectId} />;
              default: return null;
            }
          })}

          {isStreaming && !isEmpty && (
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

      <TaskHistoryPanel projectId={projectId} />

      <footer className="px-6 py-4 border-t shrink-0" style={{ borderColor: "var(--border-subtle)", background: "var(--surface-page)" }}>
        <div className="mx-auto flex gap-2" style={{ maxWidth: "var(--layout-chat-max-width)" }}>
          <div className="flex-1 flex items-center gap-2 rounded-xl px-3" style={{ background: "var(--input-bg)", border: "1px solid var(--input-border)" }}>
            <Sparkles className="size-4 shrink-0" style={{ color: "var(--text-muted)" }} />
            <Input aria-label="输入消息" placeholder={isStreaming ? "等待响应..." : "输入消息，或 /brainstorm 进入脑暴..."} value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()} disabled={isStreaming} className="border-0 focus-visible:ring-0 !shadow-none px-0" style={{ background: "transparent" }} />
          </div>
          <Button aria-label="发送" onClick={handleSend} disabled={!input.trim() || isStreaming}>
            <Send className="size-4" />
          </Button>
        </div>
      </footer>
    </div>
  );
}
