"use client";

import { useParams, useRouter } from "next/navigation";
import { useProject } from "@/lib/queries/projects";
import { formatRelative } from "@/lib/utils";
import { toneStyles, STATUS_BADGE } from "@/lib/constants";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Loader2,
  ArrowLeft,
  ListTree,
  FileText,
  Library,
  Bot,
  ArrowRight,
  BookOpen,
} from "lucide-react";
import Link from "next/link";

const subPages = [
  {
    title: "大纲",
    desc: "卷、章节、段落结构",
    href: "outline",
    icon: ListTree,
    tone: "violet",
  },
  {
    title: "写作",
    desc: "章节内容编辑",
    href: "writer",
    icon: FileText,
    tone: "emerald",
  },
  {
    title: "设定集",
    desc: "人物、世界观、组织",
    href: "settings",
    icon: Library,
    tone: "amber",
  },
  {
    title: "Agent 助手",
    desc: "AI 对话与脑暴",
    href: "agent",
    icon: Bot,
    tone: "violet",
  },
];

export default function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { data: project, isLoading } = useProject(id);

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

  if (!project) {
    return (
      <div className="p-8">
        <p style={{ color: "var(--text-tertiary)" }}>项目未找到</p>
        <Link href="/projects" className="mt-2 inline-block text-sm underline">
          返回项目列表
        </Link>
      </div>
    );
  }

  const status = STATUS_BADGE[project.status] || {
    label: project.status || "草稿",
    variant: "default" as const,
  };

  return (
    <div className="mx-auto max-w-7xl p-8">
      <Button
        variant="ghost"
        size="sm"
        onClick={() => router.back()}
        className="mb-6 -ml-1.5 text-xs text-[var(--text-tertiary)] hover:text-[var(--text-primary)]"
      >
        <ArrowLeft className="size-3.5" />
        返回
      </Button>

      {/* Project overview */}
      <Card surface="solid" className="mb-8">
        <CardHeader>
          <div className="flex flex-wrap items-center gap-2">
            <span
              className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[0.7rem] font-medium tracking-wide"
              style={{
                background: "var(--accent-subtle)",
                color: "var(--accent-text)",
              }}
            >
              <BookOpen className="size-3" />
              项目
            </span>
            {project.genre && (
              <span
                className="rounded px-1.5 py-0.5 text-xs font-medium"
                style={{
                  background: "var(--bg-elevated-hover)",
                  color: "var(--text-secondary)",
                }}
              >
                {project.genre}
              </span>
            )}
            <Badge variant={status.variant}>{status.label}</Badge>
          </div>
          <CardTitle className="mt-3 text-2xl sm:text-3xl">
            {project.title}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p
            className="max-w-3xl text-base leading-relaxed"
            style={{ color: "var(--text-secondary)" }}
          >
            {project.description || "还没有简介。"}
          </p>
          <div
            className="mt-5 flex items-center gap-5 text-xs"
            style={{ color: "var(--text-muted)" }}
          >
            <span>
              创建于{" "}
              {new Date(project.created_at).toLocaleDateString("zh-CN")}
            </span>
            <span>
              更新于 {formatRelative(project.updated_at)}
            </span>
          </div>
        </CardContent>
      </Card>

      {/* Sub-page grid */}
      <section>
        <p
          className="mb-3 text-xs font-medium uppercase tracking-wider"
          style={{ color: "var(--text-muted)" }}
        >
          创作工具
        </p>
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {subPages.map((page) => {
            const tone = toneStyles[page.tone];
            return (
              <Link key={page.href} href={`/projects/${id}/${page.href}`}>
                <Card surface="solid" className="group h-full">
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div
                        className="flex size-10 items-center justify-center rounded-lg transition-shadow duration-[var(--transition-normal)] group-hover:shadow-[0_0_18px_var(--glow)]"
                        style={{
                          background: tone.bg,
                          color: tone.text,
                          ["--glow" as string]: tone.glow,
                        }}
                      >
                        <page.icon className="size-5" />
                      </div>
                      <ArrowRight className="size-4 opacity-0 transition-opacity group-hover:opacity-100"
                        style={{ color: "var(--text-muted)" }}
                      />
                    </div>
                    <CardTitle className="mt-3 text-base">{page.title}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p
                      className="text-sm leading-relaxed"
                      style={{ color: "var(--text-tertiary)" }}
                    >
                      {page.desc}
                    </p>
                  </CardContent>
                </Card>
              </Link>
            );
          })}
        </div>
      </section>
    </div>
  );
}


