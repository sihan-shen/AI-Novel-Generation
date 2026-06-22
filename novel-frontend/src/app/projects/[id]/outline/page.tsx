"use client";

import { useParams } from "next/navigation";
import { useState } from "react";
import {
  useOutlineTree,
  useCreateOutline,
  useUpdateOutline,
  useDeleteOutline,
  type Outline,
} from "@/lib/queries/outlines";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Plus, Trash2, Loader2, ChevronRight, ChevronDown, FileText } from "lucide-react";

export default function OutlinePage() {
  const { id: projectId } = useParams<{ id: string }>();
  const { data: tree, isLoading } = useOutlineTree(projectId);
  const create = useCreateOutline(projectId);
  const remove = useDeleteOutline(projectId);

  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [newTitle, setNewTitle] = useState("");
  const [parentId, setParentId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");

  const toggle = (id: string) =>
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });

  const handleCreate = async () => {
    if (!newTitle.trim()) return;
    await create.mutateAsync({
      project_id: projectId,
      parent_id: parentId,
      title: newTitle,
    });
    setNewTitle("");
    setParentId(null);
  };

  const handleUpdate = async (id: string) => {
    if (!editTitle.trim()) return;
    await update.mutateAsync({ id, data: { title: editTitle } });
    setEditingId(null);
  };

  const update = useUpdateOutline(projectId);

  function TreeNode({ node, depth = 0 }: { node: Outline; depth?: number }) {
    const isOpen = expanded.has(node.id);
    const hasChildren = node.children && node.children.length > 0;

    return (
      <div>
        <div
          className={`flex items-center gap-1 rounded px-2 py-1.5 text-sm hover:bg-muted group`}
          style={{ paddingLeft: `${12 + depth * 20}px` }}
        >
          {hasChildren ? (
            <button onClick={() => toggle(node.id)} className="p-0.5">
              {isOpen ? (
                <ChevronDown className="size-3.5" style={{ color: "var(--text-muted)" }} />
              ) : (
                <ChevronRight className="size-3.5" style={{ color: "var(--text-muted)" }} />
              )}
            </button>
          ) : (
            <FileText className="size-3.5" style={{ color: "var(--text-secondary)" }} />
          )}

          {editingId === node.id ? (
            <div className="flex flex-1 items-center gap-1">
              <Input
                size={20}
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                className="h-7 flex-1 text-sm"
              />
              <Button size="sm" onClick={() => handleUpdate(node.id)}>
                保存
              </Button>
            </div>
          ) : (
            <span
              className="flex-1 cursor-pointer font-medium"
              onClick={() => {
                setEditingId(node.id);
                setEditTitle(node.title);
              }}
            >
              {node.title}
            </span>
          )}

          <button
            className="ml-1 rounded p-0.5 opacity-0 hover:bg-red-50 group-hover:opacity-100"
            onClick={() => remove.mutate(node.id)}
          >
            <Trash2 className="size-3 text-red-400" />
          </button>
          <button
            className="rounded p-0.5 opacity-0 hover:bg-blue-50 group-hover:opacity-100"
            onClick={() => setParentId(node.id)}
          >
            <Plus className="size-3 text-blue-400" />
          </button>
        </div>

        {isOpen &&
          hasChildren &&
          node.children.map((child) => (
            <TreeNode key={child.id} node={child} depth={depth + 1} />
          ))}
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">大纲</h1>
          <p className="mt-1 text-sm text-muted-foreground">管理卷章节结构</p>
        </div>
      </div>

      {/* Quick add */}
      <div className="mt-4 flex items-center gap-2">
        <Input
          placeholder="新增标题..."
          value={newTitle}
          onChange={(e) => setNewTitle(e.target.value)}
          className="max-w-sm"
        />
        {parentId && (
          <span className="text-xs" style={{ color: "var(--text-muted)" }}>
            添加到: {tree?.find((n) => n.id === parentId)?.title ?? parentId}
            <button className="ml-1 underline" onClick={() => setParentId(null)}>
              取消
            </button>
          </span>
        )}
        <Button size="sm" onClick={handleCreate} disabled={create.isPending}>
          <Plus className="size-4" />
          添加
        </Button>
      </div>

      {/* Tree */}
      <Card className="mt-4">
        <CardContent className="py-4">
          {isLoading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="size-6 animate-spin" style={{ color: "var(--text-muted)" }} />
            </div>
          ) : tree?.length === 0 ? (
            <p className="py-8 text-center" style={{ color: "var(--text-muted)" }}>还没有大纲节点。</p>
          ) : (
            <div className="space-y-0.5">
              {tree?.map((node) => (
                <TreeNode key={node.id} node={node} />
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
