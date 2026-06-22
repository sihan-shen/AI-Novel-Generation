"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useProjects } from "@/lib/queries/projects";
import { useIdeas } from "@/lib/queries/ideas";
import { formatRelative } from "@/lib/utils";
import { toneStyles, STATUS_LABEL } from "@/lib/constants";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  BookOpen,
  Lightbulb,
  Palette,
  ArrowRight,
  Sparkles,
  PenLine,
  Plus,
} from "lucide-react";

const quickLinks = [
  {
    title: "项目",
    desc: "管理小说项目",
    href: "/projects",
    icon: BookOpen,
    tone: "violet",
  },
  {
    title: "灵感",
    desc: "记录创作火花",
    href: "/ideas",
    icon: Lightbulb,
    tone: "amber",
  },
  {
    title: "文风",
    desc: "分析参考文风",
    href: "/styles",
    icon: Palette,
    tone: "emerald",
  },
];

export default function Dashboard() {
  const router = useRouter();
  const { data: projects } = useProjects();
  const { data: ideas } = useIdeas();

  const latestProject = projects?.length
    ? [...projects].sort(
        (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
      )[0]
    : null;

  const latestIdea = ideas?.length
    ? [...ideas].sort(
        (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      )[0]
    : null;

  return (
    <div className="mx-auto max-w-7xl p-8">
      {/* Page header */}
      <div className="mb-10">
        <span
          className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[0.7rem] font-medium tracking-wide"
          style={{
            background: "var(--accent-subtle)",
            color: "var(--accent-text)",
          }}
        >
          <Sparkles className="size-3" />
          工作台
        </span>
        <h1
          className="mt-2 text-3xl font-bold tracking-tight"
          style={{ color: "var(--text-primary)" }}
        >
          Novel Forge
        </h1>
        <p className="mt-1.5 text-sm" style={{ color: "var(--text-tertiary)" }}>
          把灵感变成故事，把故事变成小说。
        </p>
      </div>

      {/* Hero: continue creating */}
      {latestProject ? (
        <section className="mb-10">
          <p
            className="mb-2.5 text-xs font-medium uppercase tracking-wider"
            style={{ color: "var(--text-muted)" }}
          >
            继续创作
          </p>
          <Card surface="solid" className="relative overflow-hidden">
            <div
              className="pointer-events-none absolute -right-8 -top-8 size-48 rounded-full opacity-20 blur-3xl"
              style={{ background: "var(--accent-base)" }}
            />
            <CardHeader className="relative">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div className="flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className="rounded px-1.5 py-0.5 text-xs font-medium"
                      style={{
                        background: toneStyles.violet.bg,
                        color: toneStyles.violet.text,
                      }}
                    >
                      {latestProject.genre || "未分类"}
                    </span>
                    <span
                      className="text-xs"
                      style={{ color: "var(--text-muted)" }}
                    >
                      {STATUS_LABEL[latestProject.status] || latestProject.status || "草稿"}
                    </span>
                  </div>
                  <CardTitle className="mt-2.5 text-xl">{latestProject.title}</CardTitle>
                  <p
                    className="mt-1.5 line-clamp-2 max-w-2xl text-sm leading-relaxed"
                    style={{ color: "var(--text-tertiary)" }}
                  >
                    {latestProject.description || "还没有简介。"}
                  </p>
                </div>
                <Button
                  size="sm"
                  onClick={() => router.push(`/projects/${latestProject.id}`)}
                  className="shrink-0"
                >
                  进入项目
                  <ArrowRight className="size-4" />
                </Button>
              </div>
            </CardHeader>
            <CardContent className="relative">
              <div className="flex flex-col gap-2 text-xs sm:flex-row sm:items-center sm:gap-6">
                <div style={{ color: "var(--text-muted)" }}>
                  更新于 {formatRelative(latestProject.updated_at)}
                </div>
                {latestIdea && (
                  <div className="flex items-center gap-1.5" style={{ color: "var(--text-tertiary)" }}>
                    <Lightbulb className="size-3.5" style={{ color: "var(--warning-text)" }} />
                    最新灵感：
                    <Link
                      href="/ideas"
                      className="truncate max-w-[16rem] hover:underline"
                      style={{ color: "var(--accent-text)" }}
                    >
                      {latestIdea.title}
                    </Link>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </section>
      ) : (
        <Card surface="solid" className="mb-10">
          <CardHeader>
            <div className="flex items-start gap-4">
              <div
                className="flex size-12 items-center justify-center rounded-xl"
                style={{ background: "var(--accent-subtle)" }}
              >
                <PenLine className="size-6" style={{ color: "var(--accent-text)" }} />
              </div>
              <div>
                <CardTitle className="text-lg">开启你的第一部小说</CardTitle>
                <p
                  className="mt-1.5 max-w-xl text-sm leading-relaxed"
                  style={{ color: "var(--text-tertiary)" }}
                >
                  创建一个项目，然后使用 Agent 助手、大纲和写作工具把想法落地。
                </p>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <Button
              size="sm"
              onClick={() => router.push("/projects")}
            >
              <Plus className="size-4" />
              新建项目
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Quick links */}
      <section>
        <p
          className="mb-3 text-xs font-medium uppercase tracking-wider"
          style={{ color: "var(--text-muted)" }}
        >
          快捷入口
        </p>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {quickLinks.map((link) => {
            const tone = toneStyles[link.tone];
            return (
              <Link key={link.href} href={link.href}>
                <Card surface="solid" className="h-full group">
                  <CardHeader>
                    <div
                      className="mb-3 flex size-10 items-center justify-center rounded-lg transition-shadow duration-[var(--transition-normal)] group-hover:shadow-[0_0_16px_var(--glow)]"
                      style={{
                        background: tone.bg,
                        color: tone.text,
                        ["--glow" as string]: tone.glow,
                      }}
                    >
                      <link.icon className="size-[18px]" />
                    </div>
                    <CardTitle className="flex items-center gap-1.5 text-base">
                      {link.title}
                      <ArrowRight className="size-3.5 opacity-0 transition-opacity group-hover:opacity-100" />
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p
                      className="text-sm leading-relaxed"
                      style={{ color: "var(--text-tertiary)" }}
                    >
                      {link.desc}
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
