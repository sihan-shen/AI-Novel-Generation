"use client";

import { useConfig, useSaveConfig, type ConfigMap } from "@/lib/queries/config";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Loader2, Save } from "lucide-react";
import { useState, useEffect } from "react";

const FIELD_LABELS: Record<string, string> = {
  llm_provider: "LLM 提供商",
  api_key: "API Key",
  base_url: "Base URL",
  model: "模型",
  host: "监听地址",
  port: "端口",
};

export default function ConfigPage() {
  const { data: config, isLoading } = useConfig();
  const save = useSaveConfig();
  const [form, setForm] = useState<ConfigMap>({});

  useEffect(() => {
    if (config) setForm(config);
  }, [config]);

  const handleChange = (key: string, value: string) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleSave = () => save.mutate(form);

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
            配置
          </span>
          <h1 className="mt-2 text-2xl font-bold tracking-tight" style={{ color: "var(--text-primary)" }}>
            配置
          </h1>
          <p className="mt-1 text-sm" style={{ color: "var(--text-tertiary)" }}>
            应用和 LLM 设置
          </p>
        </div>
        <Button size="sm" onClick={handleSave} disabled={save.isPending}>
          <Save className="size-4" />
          {save.isPending ? "保存中..." : "保存"}
        </Button>
      </div>

      <div className="mt-6 grid gap-6 sm:grid-cols-2">
        {Object.entries(FIELD_LABELS).map(([key, label]) => (
          <div key={key} className="space-y-1.5">
            <label htmlFor={key} className="text-sm font-medium" style={{ color: "var(--text-secondary)" }}>
              {label}
            </label>
            <Input
              id={key}
              value={form[key] ?? ""}
              onChange={(e) => handleChange(key, e.target.value)}
              type={key === "api_key" ? "password" : "text"}
            />
          </div>
        ))}
      </div>

      {save.data && (
        <p className="mt-4 text-sm" style={{ color: "var(--success-text)" }}>
          配置已保存。
        </p>
      )}
    </div>
  );
}
