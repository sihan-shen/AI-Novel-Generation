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
        <Loader2 className="size-6 animate-spin text-zinc-400" />
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">灵感</h1>
          <p className="mt-1 text-sm text-zinc-500">随手记录创作灵感</p>
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
        <Button
          size="sm"
          onClick={handleCreate}
          disabled={create.isPending}
        >
          <Plus className="size-4" />
          添加
        </Button>
      </div>

      {/* 列表 */}
      <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {ideas?.map((idea) => (
          <Card key={idea.id} className="group relative">
            <CardHeader>
              <CardTitle className="flex items-start gap-2 text-base">
                <Lightbulb className="mt-0.5 size-4 text-amber-500 shrink-0" />
                {idea.title}
              </CardTitle>
            </CardHeader>
            {idea.content && (
              <CardContent>
                <p className="line-clamp-3 text-sm text-zinc-500">{idea.content}</p>
              </CardContent>
            )}
            <button
              className="absolute right-2 top-2 rounded p-1 opacity-0 transition-opacity hover:bg-red-50 group-hover:opacity-100"
              onClick={() => remove.mutate(idea.id)}
            >
              <Trash2 className="size-3.5 text-red-500" />
            </button>
          </Card>
        ))}
      </div>

      {ideas?.length === 0 && (
        <p className="mt-16 text-center text-zinc-400">还没有灵感记录。</p>
      )}
    </div>
  );
}
