"use client";

import { useParams, useRouter } from "next/navigation";
import { useProject } from "@/lib/queries/projects";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Loader2, ArrowLeft } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { data: project, isLoading } = useProject(id);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-16">
        <Loader2 className="size-6 animate-spin text-zinc-400" />
      </div>
    );
  }

  if (!project) {
    return (
      <div className="p-8">
        <p className="text-zinc-500">项目未找到</p>
        <Link href="/projects" className="mt-2 inline-block text-sm underline">
          返回项目列表
        </Link>
      </div>
    );
  }

  return (
    <div className="p-8">
      <Button variant="ghost" size="sm" onClick={() => router.back()} className="mb-4">
        <ArrowLeft className="size-4" />
        返回
      </Button>

      <Card>
        <CardHeader>
          <CardTitle className="text-2xl">{project.title}</CardTitle>
          {project.genre && (
            <span className="text-sm text-zinc-500">{project.genre}</span>
          )}
        </CardHeader>
        <CardContent>
          <p className="text-zinc-600 dark:text-zinc-400">
            {project.description || "暂无简介"}
          </p>
          <div className="mt-6 flex gap-3">
            <span className="rounded bg-zinc-100 px-2 py-0.5 text-xs dark:bg-zinc-800">
              {project.status || "草稿"}
            </span>
            <span className="text-xs text-zinc-400">
              创建于 {new Date(project.created_at).toLocaleDateString("zh-CN")}
            </span>
          </div>
        </CardContent>
      </Card>

      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        <SubPageCard title="大纲" desc="管理卷章节结构" href={`/projects/${id}/outline`} />
        <SubPageCard title="写作" desc="章节内容编辑" href={`/projects/${id}/writer`} />
        <SubPageCard title="设定集" desc="人物、世界观、组织" href={`/projects/${id}/settings`} />
        <SubPageCard title="审阅" desc="四维自动审阅" href={`/projects/${id}/review`} />
        <SubPageCard title="Agent 助手" desc="AI 对话与脑暴" href={`/projects/${id}/agent`} />
      </div>
    </div>
  );
}

function SubPageCard({ title, desc, href }: { title: string; desc: string; href: string }) {
  return (
    <Link href={href}>
      <Card className="transition-colors hover:bg-zinc-50 dark:hover:bg-zinc-900">
        <CardHeader>
          <CardTitle className="text-base">{title}</CardTitle>
          <p className="text-sm text-zinc-500">{desc}</p>
        </CardHeader>
      </Card>
    </Link>
  );
}
