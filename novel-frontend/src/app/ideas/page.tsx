"use client";

import { useState } from "react";
import { useIdeas, useCreateIdea, useDeleteIdea } from "@/lib/queries/ideas";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Plus, Trash2, Loader2, Lightbulb } from "lucide-react";

export default function IdeasPage() {
  const { data: ideas, isLoading } = useIdeas();
  const create = useCreateIdea();
  const remove = useDeleteIdea();
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");

  const handleCreate = async () => {
    if (!title.trim()) return;
    await create.mutateAsync({ title, content });
    setTitle("");
    setContent("");
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-16">
        <Loader2 className="size-6 animate-spin" style={{ color: "var(--accent-base)" }} />
      </div>
    );
  }

  return (
    <div className="p-8">
      {/* Page header */}
      <div className="mb-8 flex items-end justify-between">
        <div>
          <span
            className="inline-block rounded-full px-2.5 py-0.5 text-[0.7rem] font-medium tracking-wide"
            style={{ background: "var(--accent-subtle)", color: "var(--accent-text)" }}
          >
            灵感
          </span>
          <h1 className="mt-2 text-2xl font-bold tracking-tight" style={{ color: "var(--text-primary)" }}>
            灵感
          </h1>
          <p className="mt-1 text-sm" style={{ color: "var(--text-tertiary)" }}>
            随手记录创作灵感
          </p>
        </div>
      </div>

      {/* 快速录入 */}
      <div className="mt-6 flex gap-2">
        <Input
          placeholder="标题..."
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="max-w-xs"
        />
        <Input
          placeholder="内容（可选）"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          className="flex-1"
        />
        <Button size="sm" onClick={handleCreate} disabled={create.isPending}>
          <Plus className="size-4" />
          添加
        </Button>
      </div>

      {/* 列表 */}
      <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {ideas?.map((idea) => (
          <Card key={idea.id} className="group relative" surface="solid">
            <CardHeader>
              <CardTitle className="flex items-start gap-2 text-base">
                <Lightbulb className="mt-0.5 size-4 shrink-0" style={{ color: "var(--warning-text)" }} />
                {idea.title}
              </CardTitle>
            </CardHeader>
            {idea.content && (
              <CardContent>
                <p className="line-clamp-3 text-sm" style={{ color: "var(--text-tertiary)" }}>
                  {idea.content}
                </p>
              </CardContent>
            )}
            <button
              className="absolute right-2 top-2 rounded p-1 opacity-0 transition-opacity hover:bg-[var(--danger-subtle)] group-hover:opacity-100"
              style={{ color: "var(--danger-text)" }}
              onClick={() => remove.mutate(idea.id)}
              aria-label="删除灵感"
            >
              <Trash2 className="size-3.5" />
            </button>
          </Card>
        ))}
      </div>

      {ideas?.length === 0 && (
        <p className="mt-16 text-center" style={{ color: "var(--text-muted)" }}>
          还没有灵感记录。
        </p>
      )}
    </div>
  );
}
