"use client";

import Link from "next/link";
import { useProjects, useCreateProject, useDeleteProject } from "@/lib/queries/projects";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Plus, Trash2, Loader2 } from "lucide-react";
import { useState } from "react";

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
        <Loader2 className="size-6 animate-spin text-zinc-400" />
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">项目</h1>
          <p className="mt-1 text-sm text-zinc-500">管理你的小说项目</p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger>
            <Button size="sm">
              <Plus className="size-4" />
              新建项目
            </Button>
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
          <Card key={p.id} className="group relative">
            <Link href={`/projects/${p.id}`}>
              <CardHeader>
                <CardTitle className="text-lg">{p.title}</CardTitle>
                {p.genre && (
                  <span className="text-xs text-zinc-500">{p.genre}</span>
                )}
              </CardHeader>
              <CardContent>
                <p className="line-clamp-2 text-sm text-zinc-500">
                  {p.description || "暂无简介"}
                </p>
                <span className="mt-2 inline-block rounded bg-zinc-100 px-2 py-0.5 text-xs dark:bg-zinc-800">
                  {p.status || "草稿"}
                </span>
              </CardContent>
            </Link>
            <button
              className="absolute right-3 top-3 rounded p-1 opacity-0 transition-opacity hover:bg-red-50 group-hover:opacity-100"
              onClick={() => remove.mutate(p.id)}
              aria-label="删除项目"
            >
              <Trash2 className="size-4 text-red-500" />
            </button>
          </Card>
        ))}
      </div>

      {projects?.length === 0 && (
        <p className="mt-16 text-center text-zinc-400">还没有项目，创建一个吧。</p>
      )}
    </div>
  );
}
