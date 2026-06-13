import Link from "next/link";
import { FileQuestion } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function NotFoundPage() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 text-center">
      <FileQuestion className="size-12" style={{ color: "var(--text-muted)" }} />
      <h2 className="text-2xl font-bold tracking-tight" style={{ color: "var(--text-primary)" }}>页面未找到</h2>
      <p className="text-sm" style={{ color: "var(--text-tertiary)" }}>你访问的页面不存在或已被移除。</p>
      <Link href="/">
        <Button variant="outline" size="sm">返回工作台</Button>
      </Link>
    </div>
  );
}
