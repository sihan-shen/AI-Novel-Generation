"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { AlertTriangle } from "lucide-react";

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Unhandled page error:", error);
  }, [error]);

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 text-center">
      <AlertTriangle className="size-10 text-amber-500" />
      <h2 className="text-xl font-semibold">出了点问题</h2>
      <p className="max-w-md text-sm text-zinc-500">
        {error.message || "页面加载出错，请重试。"}
      </p>
      <Button onClick={reset} variant="outline" size="sm">
        重试
      </Button>
    </div>
  );
}
