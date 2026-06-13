"use client";

import { useStyles, useDeleteStyle } from "@/lib/queries/styles";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Trash2, Loader2, Palette } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function StylesPage() {
  const { data: styles, isLoading } = useStyles();
  const remove = useDeleteStyle();

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
            style={{ background: "var(--accent-subtle)", color: "var(--accent-text)" }}
          >
            文风库
          </span>
          <h1 className="mt-2 text-2xl font-bold tracking-tight" style={{ color: "var(--text-primary)" }}>
            文风库
          </h1>
          <p className="mt-1 text-sm" style={{ color: "var(--text-tertiary)" }}>
            管理和分析参考文风
          </p>
        </div>
        <Button variant="outline" size="sm" disabled>
          导入文风
        </Button>
      </div>

      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        {styles?.map((s) => (
          <Card key={s.id} className="group relative" surface="solid">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Palette className="size-4" style={{ color: "var(--accent-text)" }} />
                {s.name}
              </CardTitle>
              <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                {s.source}
              </span>
            </CardHeader>
            {s.analysis && (
              <CardContent>
                <ScrollArea className="h-24">
                  <p className="whitespace-pre-wrap text-sm" style={{ color: "var(--text-tertiary)" }}>
                    {s.analysis}
                  </p>
                </ScrollArea>
              </CardContent>
            )}
            <button
              className="absolute right-3 top-3 rounded p-1 opacity-0 transition-opacity hover:bg-[var(--danger-subtle)] group-hover:opacity-100"
              style={{ color: "var(--danger-text)" }}
              onClick={() => remove.mutate(s.id)}
              aria-label="删除文风"
            >
              <Trash2 className="size-4" />
            </button>
          </Card>
        ))}
      </div>

      {styles?.length === 0 && (
        <p className="mt-16 text-center" style={{ color: "var(--text-muted)" }}>
          还没有文风记录。
        </p>
      )}
    </div>
  );
}
