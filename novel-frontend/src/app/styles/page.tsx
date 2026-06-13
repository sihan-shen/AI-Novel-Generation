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
        <Loader2 className="size-6 animate-spin text-zinc-400" />
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">文风库</h1>
          <p className="mt-1 text-sm text-zinc-500">管理和分析参考文风</p>
        </div>
        <Button variant="outline" size="sm" disabled>
          导入文风
        </Button>
      </div>

      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        {styles?.map((s) => (
          <Card key={s.id} className="group relative">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Palette className="size-4 text-purple-500" />
                {s.name}
              </CardTitle>
              <span className="text-xs text-zinc-400">{s.source}</span>
            </CardHeader>
            {s.analysis && (
              <CardContent>
                <ScrollArea className="h-24">
                  <p className="whitespace-pre-wrap text-sm text-zinc-500">
                    {s.analysis}
                  </p>
                </ScrollArea>
              </CardContent>
            )}
            <button
              className="absolute right-3 top-3 rounded p-1 opacity-0 transition-opacity hover:bg-red-50 group-hover:opacity-100"
              onClick={() => remove.mutate(s.id)}
            >
              <Trash2 className="size-4 text-red-500" />
            </button>
          </Card>
        ))}
      </div>

      {styles?.length === 0 && (
        <p className="mt-16 text-center text-zinc-400">还没有文风记录。</p>
      )}
    </div>
  );
}
