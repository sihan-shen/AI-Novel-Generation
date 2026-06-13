"use client";

import { useParams } from "next/navigation";
import { useState } from "react";
import {
  useChapters,
  useCreateChapter,
  useUpdateChapter,
  useDeleteChapter,
} from "@/lib/queries/chapters";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Plus, Trash2, Loader2, FileText } from "lucide-react";

export default function WriterPage() {
  const { id: projectId } = useParams<{ id: string }>();
  const { data: chapters, isLoading } = useChapters(projectId);
  const create = useCreateChapter(projectId);
  const update = useUpdateChapter(projectId);
  const remove = useDeleteChapter(projectId);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [newTitle, setNewTitle] = useState("");
  const [editContent, setEditContent] = useState("");

  const selected = chapters?.find((c) => c.id === selectedId);

  const handleCreate = async () => {
    if (!newTitle.trim()) return;
    await create.mutateAsync({ title: newTitle, project_id: projectId });
    setNewTitle("");
  };

  const handleSave = async () => {
    if (!selectedId) return;
    await update.mutateAsync({ id: selectedId, data: { content: editContent } });
  };

  const handleSelect = (chapter: { id: string; content: string }) => {
    setSelectedId(chapter.id);
    setEditContent(chapter.content);
  };

  return (
    <div className="flex h-full">
      {/* Sidebar */}
      <aside className="w-56 shrink-0 border-r bg-zinc-50 dark:bg-zinc-950">
        <div className="p-3">
          <h2 className="mb-2 text-sm font-semibold text-zinc-500">章节</h2>
          <div className="flex gap-1">
            <Input
              placeholder="新章节..."
              size={20}
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              className="h-7 text-xs"
            />
            <Button
              size="sm"
              variant="ghost"
              className="h-7 px-2"
              onClick={handleCreate}
            >
              <Plus className="size-3" />
            </Button>
          </div>
        </div>
        <ScrollArea className="h-[calc(100vh-5rem)]">
          {isLoading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="size-5 animate-spin text-zinc-400" />
            </div>
          ) : (
            <div className="space-y-0.5 px-2">
              {chapters?.map((c) => (
                <button
                  key={c.id}
                  onClick={() => handleSelect(c)}
                  className={`flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm transition-colors ${
                    selectedId === c.id
                      ? "bg-zinc-200 font-medium dark:bg-zinc-800"
                      : "hover:bg-zinc-100 dark:hover:bg-zinc-800"
                  }`}
                >
                  <FileText className="size-3.5 shrink-0 text-zinc-400" />
                  <span className="flex-1 truncate">{c.title}</span>
                  <button
                    className="rounded p-0.5 opacity-0 hover:bg-red-50 group-hover:opacity-100"
                    onClick={(e) => {
                      e.stopPropagation();
                      remove.mutate(c.id);
                    }}
                  >
                    <Trash2 className="size-3 text-red-400" />
                  </button>
                </button>
              ))}
            </div>
          )}
        </ScrollArea>
      </aside>

      {/* Editor */}
      <main className="flex-1 p-8">
        {selected ? (
          <div className="mx-auto max-w-3xl space-y-4">
            <div className="flex items-center justify-between">
              <h1 className="text-xl font-bold">{selected.title}</h1>
              <Button size="sm" onClick={handleSave} disabled={update.isPending}>
                {update.isPending ? "保存中..." : "保存"}
              </Button>
            </div>
            <textarea
              className="min-h-[60vh] w-full resize-y rounded-lg border p-4 font-mono text-sm leading-relaxed"
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              placeholder="章节内容..."
            />
          </div>
        ) : (
          <div className="flex h-full items-center justify-center text-zinc-400">
            {chapters?.length
              ? "从左侧选择一个章节开始编辑"
              : "新建一个章节开始写作"}
          </div>
        )}
      </main>
    </div>
  );
}
