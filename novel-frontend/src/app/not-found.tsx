import Link from "next/link";
import { FileQuestion } from "lucide-react";

export default function NotFoundPage() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 text-center">
      <FileQuestion className="size-12 text-zinc-300" />
      <h2 className="text-2xl font-bold tracking-tight">页面未找到</h2>
      <p className="text-sm text-zinc-500">你访问的页面不存在或已被移除。</p>
      <Link href="/" className="inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm font-medium transition-colors hover:bg-zinc-50 dark:hover:bg-zinc-900">
        返回工作台
      </Link>
    </div>
  );
}
