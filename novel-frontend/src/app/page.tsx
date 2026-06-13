import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { BookOpen, Lightbulb, Palette } from "lucide-react";
import Link from "next/link";

const navCards = [
  {
    title: "最近项目",
    desc: "查看和管理你的小说项目",
    href: "/projects",
    icon: BookOpen,
    gradient: "linear-gradient(135deg, rgba(124,58,237,0.15), rgba(139,92,246,0.05))",
    iconColor: "var(--accent-text)",
  },
  {
    title: "灵感记录",
    desc: "随手记录创作灵感",
    href: "/ideas",
    icon: Lightbulb,
    gradient: "linear-gradient(135deg, rgba(251,191,36,0.15), rgba(251,191,36,0.05))",
    iconColor: "#fbbf24",
  },
  {
    title: "文风库",
    desc: "管理和分析参考文风",
    href: "/styles",
    icon: Palette,
    gradient: "linear-gradient(135deg, rgba(52,211,153,0.15), rgba(52,211,153,0.05))",
    iconColor: "#34d399",
  },
];

export default function Dashboard() {
  return (
    <div className="p-8">
      {/* Page header */}
      <div className="mb-8">
        <span
          className="inline-block rounded-full px-2.5 py-0.5 text-[0.7rem] font-medium tracking-wide"
          style={{
            background: "var(--accent-subtle)",
            color: "var(--accent-text)",
          }}
        >
          工作台
        </span>
        <h1
          className="mt-2 text-2xl font-bold tracking-tight"
          style={{ color: "var(--text-primary)" }}
        >
          Novel Forge
        </h1>
        <p className="mt-1 text-sm" style={{ color: "var(--text-tertiary)" }}>
          欢迎回来，继续你的创作之旅。
        </p>
      </div>

      {/* Navigation cards */}
      <div
        className="grid gap-4"
        style={{
          gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))",
        }}
      >
        {navCards.map((card) => (
          <Link key={card.href} href={card.href}>
            <Card
              className="h-full cursor-pointer"
              surface="solid"
            >
              <CardHeader>
                <div
                  className="flex size-8 items-center justify-center rounded-lg mb-2"
                  style={{ background: card.gradient }}
                >
                  <card.icon className="size-4" style={{ color: card.iconColor }} />
                </div>
                <CardTitle className="text-base">{card.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm leading-relaxed" style={{ color: "var(--text-tertiary)" }}>
                  {card.desc}
                </p>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
