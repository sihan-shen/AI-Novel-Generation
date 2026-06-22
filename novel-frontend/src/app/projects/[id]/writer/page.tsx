"use client";

import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import {
  useChapters,
  useCreateChapter,
  useUpdateChapter,
  useDeleteChapter,
} from "@/lib/queries/chapters";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Plus, Trash2, Loader2, FileText, Sparkles } from "lucide-react";

export default function WriterPage() {
  const { id: projectId } = useParams<{ id: string }>();
  const router = useRouter();
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
      {/* Chapter sidebar */}
      <aside
        className="w-[var(--layout-writer-sidebar)] shrink-0 border-r flex flex-col"
        style={{
          background: "var(--surface-editor-sidebar)",
          borderColor: "var(--border-subtle)",
        }}
      >
        <div className="p-3">
          <h2 className="mb-2 text-xs font-semibold tracking-wide" style={{ color: "var(--text-tertiary)" }}>
            章节
          </h2>
          <div className="flex gap-1">
            <Input
              placeholder="新章节..."
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              className="h-7 text-xs"
            />
            <Button size="sm" variant="ghost" className="h-7 px-2" onClick={handleCreate}>
              <Plus className="size-3" />
            </Button>
          </div>
        </div>
        <ScrollArea className="flex-1">
          {isLoading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="size-5 animate-spin" style={{ color: "var(--accent-base)" }} />
            </div>
          ) : (
            <div className="space-y-0.5 px-2">
              {chapters?.map((c) => (
                <button
                  key={c.id}
                  onClick={() => handleSelect(c)}
                  className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm transition-colors"
                  style={{
                    background: selectedId === c.id ? "var(--nav-item-active-bg)" : "transparent",
                    color: selectedId === c.id ? "var(--nav-item-active-text)" : "var(--nav-item-text)",
                  }}
                >
                  <FileText className="size-3.5 shrink-0" style={{ color: "var(--text-muted)" }} />
                  <span className="flex-1 truncate">{c.title}</span>
                  <button
                    className="rounded p-0.5 opacity-0 hover:bg-[var(--danger-subtle)]"
                    onClick={(e) => {
                      e.stopPropagation();
                      remove.mutate(c.id);
                    }}
                  >
                    <Trash2 className="size-3" style={{ color: "var(--danger-text)" }} />
                  </button>
                </button>
              ))}
            </div>
          )}
        </ScrollArea>
      </aside>

      {/* Editor */}
      <main
        className="flex-1 flex flex-col"
        style={{ background: "var(--surface-editor)" }}
      >
        {selected ? (
          <>
            {/* Toolbar */}
            <div
              className="flex items-center justify-between px-6 py-3 border-b"
              style={{ borderColor: "var(--border-subtle)" }}
            >
              <div className="flex items-center gap-2">
                <div
                  className="w-0.5 h-5 rounded-full"
                  style={{ background: "var(--accent-base)" }}
                />
                <span className="text-sm" style={{ color: "var(--text-tertiary)" }}>
                  {selected.title}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="ghost"
                  className="h-7"
                  disabled={!selectedId}
                  onClick={() => {
                    if (!selectedId) return;
                    router.push(
                      `/projects/${projectId}/agent?chapter=${selectedId}&mode=writing`,
                    );
                  }}
                >
                  <Sparkles className="size-3.5 mr-1" />
                  AI
                </Button>
                <Button size="sm" onClick={handleSave} disabled={update.isPending}>
                  {update.isPending ? "保存中..." : "保存"}
                </Button>
              </div>
            </div>

            {/* Content area */}
            <div className="flex-1 overflow-auto">
              <div
                className="mx-auto p-8"
                style={{ maxWidth: "var(--layout-writer-max-width)" }}
              >
                <textarea
                  className="w-full min-h-[60vh] resize-y rounded-lg p-4 text-sm leading-relaxed border-0 focus:ring-0"
                  style={{
                    background: "transparent",
                    color: "var(--editor-text)",
                    caretColor: "var(--editor-cursor)",
                    fontFamily: "var(--font-mono)",
                    lineHeight: "1.85",
                  }}
                  value={editContent}
                  onChange={(e) => setEditContent(e.target.value)}
                  placeholder="章节内容..."
                />
              </div>
            </div>

            {/* Status bar */}
            <div
              className="flex items-center justify-between px-6 py-2 border-t text-[0.7rem]"
              style={{
                borderColor: "var(--border-subtle)",
                color: "var(--text-muted)",
              }}
            >
              <span>字数: {editContent.length}</span>
              <span>自动保存</span>
            </div>
          </>
        ) : (
          <div
            className="flex h-full items-center justify-center"
            style={{ color: "var(--text-muted)" }}
          >
            {chapters?.length
              ? "从左侧选择一个章节开始编辑"
              : "新建一个章节开始写作"}
          </div>
        )}
      </main>
    </div>
  );
}
