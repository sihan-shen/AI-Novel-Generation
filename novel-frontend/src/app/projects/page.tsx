"use client";

import Link from "next/link";
import { useState } from "react";
import {
  useProjects,
  useCreateProject,
  useDeleteProject,
} from "@/lib/queries/projects";
import { formatRelative } from "@/lib/utils";
import { STATUS_BADGE } from "@/lib/constants";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Plus, Trash2, Loader2, BookOpen, ArrowRight } from "lucide-react";

const STATUS_PROGRESS: Record<string, number> = {
  draft: 0,
  writing: 0.5,
  completed: 1,
};

const TAG_COLORS = [
  { bg: "var(--accent-subtle)", text: "var(--accent-text)" },
  { bg: "var(--info-subtle)", text: "var(--info-text)" },
  { bg: "var(--success-subtle)", text: "var(--success-text)" },
  { bg: "var(--warning-subtle)", text: "var(--warning-text)" },
  { bg: "var(--danger-subtle)", text: "var(--danger-text)" },
  { bg: "var(--processing-subtle)", text: "var(--processing-text)" },
];

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
        <Loader2
          className="size-6 animate-spin"
          style={{ color: "var(--accent-base)" }}
        />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl p-8">
      {/* Page header */}
      <div className="mb-10 flex items-end justify-between gap-4">
        <div>
          <span
            className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[0.7rem] font-medium tracking-wide"
            style={{
              background: "var(--accent-subtle)",
              color: "var(--accent-text)",
            }}
          >
            <BookOpen className="size-3" />
            项目
          </span>
          <h1
            className="mt-3 text-3xl font-bold tracking-tight"
            style={{ color: "var(--text-primary)" }}
          >
            小说项目
          </h1>
          <p className="mt-1.5 text-sm" style={{ color: "var(--text-tertiary)" }}>
            {projects?.length
              ? `共 ${projects.length} 个项目`
              : "从这里开始，把灵感变成完整的小说。"}
          </p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <Button size="sm" onClick={() => setOpen(true)}>
            <Plus className="size-4" />
            新建项目
          </Button>
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

      {/* Project grid */}
      {projects && projects.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((project) => (
            <ProjectCard
              key={project.id}
              project={project}
              onDelete={() => remove.mutate(project.id)}
            />
          ))}
        </div>
      ) : (
        <EmptyState onCreate={() => setOpen(true)} />
      )}
    </div>
  );
}

function ProjectCard({
  project,
  onDelete,
}: {
  project: {
    id: string;
    title: string;
    description: string;
    genre: string;
    status: string;
    updated_at: string;
  };
  onDelete: () => void;
}) {
  const status = STATUS_BADGE[project.status] || {
    label: project.status || "草稿",
    variant: "default" as const,
  };
  const progress = STATUS_PROGRESS[project.status] ?? 0;
  const tagColor = project.genre ? colorForTag(project.genre) : null;

  return (
    <Card surface="solid" className="group relative flex h-full flex-col">
      <Link href={`/projects/${project.id}`} className="flex flex-1 flex-col">
        <CardHeader className="flex-1">
          <div className="flex items-start justify-between gap-3">
            <div className="flex flex-wrap items-center gap-2">
              {tagColor && (
                <span
                  className="rounded px-1.5 py-0.5 text-xs font-medium"
                  style={{ background: tagColor.bg, color: tagColor.text }}
                >
                  {project.genre}
                </span>
              )}
              <StatusBadge status={status} />
            </div>
          </div>
          <CardTitle className="mt-2.5 text-lg">{project.title}</CardTitle>
          <p
            className="mt-1.5 line-clamp-2 text-sm leading-relaxed"
            style={{ color: "var(--text-tertiary)" }}
          >
            {project.description || "暂无简介"}
          </p>
        </CardHeader>
        <CardContent className="pt-0">
          <div className="space-y-3">
            <div className="flex items-center justify-between text-xs"
              style={{ color: "var(--text-muted)" }}
            >
              <span>{formatRelative(project.updated_at)}</span>
              <span className="flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100"
                style={{ color: "var(--accent-text)" }}
              >
                查看
                <ArrowRight className="size-3" />
              </span>
            </div>
            {/* Progress bar signature */}
            <div
              className="h-1.5 w-full overflow-hidden rounded-full"
              style={{ background: "var(--bg-elevated-hover)" }}
            >
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{
                  width: `${progress * 100}%`,
                  background:
                    progress === 1
                      ? "var(--success-base)"
                      : "var(--gradient-accent)",
                }}
              />
            </div>
          </div>
        </CardContent>
      </Link>
      <button
        className="absolute right-2 top-2 rounded p-1 opacity-0 transition-all hover:bg-[var(--danger-subtle)] group-hover:opacity-100"
        style={{ color: "var(--danger-text)" }}
        onClick={(e) => {
          e.preventDefault();
          onDelete();
        }}
        aria-label="删除项目"
      >
        <Trash2 className="size-4" />
      </button>
    </Card>
  );
}

function StatusBadge({
  status,
}: {
  status: { label: string; variant: "default" | "processing" | "success" };
}) {
  const styles = {
    default: { bg: "var(--badge-default-bg)", text: "var(--badge-default-text)" },
    processing: { bg: "var(--badge-processing-bg)", text: "var(--badge-processing-text)" },
    success: { bg: "var(--badge-success-bg)", text: "var(--badge-success-text)" },
  }[status.variant];

  return (
    <span
      className="rounded px-1.5 py-0.5 text-xs font-medium"
      style={{ background: styles.bg, color: styles.text }}
    >
      {status.label}
    </span>
  );
}

function EmptyState({ onCreate }: { onCreate: () => void }) {
  return (
    <Card surface="solid" className="py-16">
      <CardContent className="flex flex-col items-center text-center">
        <div
          className="mb-4 flex size-14 items-center justify-center rounded-2xl"
          style={{ background: "var(--accent-subtle)" }}
        >
          <BookOpen className="size-7" style={{ color: "var(--accent-text)" }} />
        </div>
        <p
          className="text-base font-medium"
          style={{ color: "var(--text-primary)" }}
        >
          还没有项目
        </p>
        <p
          className="mx-auto mt-1 max-w-xs text-sm"
          style={{ color: "var(--text-tertiary)" }}
        >
          创建一个项目，开始规划大纲、记录灵感，并让 AI 协助你写作。
        </p>
        <Button onClick={onCreate} className="mt-5" size="sm">
          <Plus className="size-4" />
          新建项目
        </Button>
      </CardContent>
    </Card>
  );
}


