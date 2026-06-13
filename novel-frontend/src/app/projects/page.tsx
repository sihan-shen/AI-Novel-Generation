"use client";

import Link from "next/link";
import { useProjects, useCreateProject, useDeleteProject } from "@/lib/queries/projects";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Plus, Trash2, Loader2 } from "lucide-react";
import { useState } from "react";

const TAG_COLORS = [
  { bg: "var(--accent-subtle)", text: "var(--accent-text)" },
  { bg: "var(--info-subtle)", text: "var(--info-text)" },
  { bg: "var(--success-subtle)", text: "var(--success-text)" },
  { bg: "var(--warning-subtle)", text: "var(--warning-text)" },
  { bg: "var(--danger-subtle)", text: "var(--danger-text)" },
  { bg: "var(--processing-subtle)", text: "var(--processing-text)" },
];

const STATUS_BADGE: Record<string, "default" | "processing" | "success"> = {
  draft: "default",
  writing: "processing",
  completed: "success",
};

function colorForTag(tag: string) {
  const i = tag
    .split("")
    .reduce((acc, c) => acc + c.charCodeAt(0), 0) % TAG_COLORS.length;
  return TAG_COLORS[i];
}

export default function ProjectsPage() {
  const { data: projects, isLoading } = useProjects();
  const create = useCreateProject();
  const remove = useDeleteProject();
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [genre, setGenre] = useState("");

  const handleCreate = async () => {
    if (!title.trim()) return;
    await create.mutateAsync({ title, genre: genre || undefined });
    setTitle("");
    setGenre("");
    setOpen(false);
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
            style={{
              background: "var(--accent-subtle)",
              color: "var(--accent-text)",
            }}
          >
            项目
          </span>
          <h1
            className="mt-2 text-2xl font-bold tracking-tight"
            style={{ color: "var(--text-primary)" }}
          >
            项目
          </h1>
          <p className="mt-1 text-sm" style={{ color: "var(--text-tertiary)" }}>
            管理你的小说项目
          </p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger
            className="inline-flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition-colors"
            style={{
              background: "var(--button-primary-bg)",
              color: "var(--button-primary-text)",
            }}
          >
            <Plus className="size-4" />
            新建项目
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>新建项目</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <Input
                placeholder="项目名称"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
              <Input
                placeholder="类型（如：科幻、奇幻...）"
                value={genre}
                onChange={(e) => setGenre(e.target.value)}
              />
              <Button
                onClick={handleCreate}
                disabled={create.isPending}
                className="w-full"
              >
                {create.isPending ? "创建中..." : "创建"}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {projects?.map((p) => (
          <Card key={p.id} className="group relative" surface="solid">
            <Link href={`/projects/${p.id}`}>
              <CardHeader>
                <CardTitle className="text-lg">{p.title}</CardTitle>
                {p.genre && (
                  <span
                    className="inline-block rounded px-1.5 py-0.5 text-xs font-medium"
                    style={{
                      background: colorForTag(p.genre).bg,
                      color: colorForTag(p.genre).text,
                    }}
                  >
                    {p.genre}
                  </span>
                )}
              </CardHeader>
              <CardContent>
                <p className="line-clamp-2 text-sm" style={{ color: "var(--text-tertiary)" }}>
                  {p.description || "暂无简介"}
                </p>
                <Badge
                  className="mt-2"
                  variant={STATUS_BADGE[p.status as keyof typeof STATUS_BADGE] || "default"}
                >
                  {p.status || "草稿"}
                </Badge>
              </CardContent>
            </Link>
            <button
              className="absolute right-3 top-3 rounded p-1 opacity-0 transition-opacity hover:bg-[var(--danger-subtle)] group-hover:opacity-100"
              style={{ color: "var(--danger-text)" }}
              onClick={() => remove.mutate(p.id)}
              aria-label="删除项目"
            >
              <Trash2 className="size-4" />
            </button>
          </Card>
        ))}
      </div>

      {projects?.length === 0 && (
        <p className="mt-16 text-center" style={{ color: "var(--text-muted)" }}>
          还没有项目，创建一个吧。
        </p>
      )}
    </div>
  );
}
