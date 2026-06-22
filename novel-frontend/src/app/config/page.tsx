"use client";

import { useState } from "react";
import { useConfig, useSaveConfig, useFetchModels, type ConfigMap, type ConfigSaveInput } from "@/lib/queries/config";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Loader2, Save, Wrench, RefreshCw, KeyRound, CheckCircle2, AlertCircle } from "lucide-react";

/* ------------------------------------------------------------------ */
/*  Provider metadata (mirrors backend provider_registry.py)           */
/* ------------------------------------------------------------------ */

interface ProviderInfo {
  id: string;
  label: string;
  needsApiKey: boolean;
  needsBaseUrl: boolean;
  presets: string[];
  defaultModel: string;
}

const PROVIDERS: Record<string, ProviderInfo> = {
  claude: {
    id: "claude", label: "Claude (Anthropic)",
    needsApiKey: true, needsBaseUrl: false,
    presets: ["claude-sonnet-4-6", "claude-opus-4-7", "claude-haiku-4-5-20251001"],
    defaultModel: "claude-sonnet-4-6",
  },
  openai: {
    id: "openai", label: "OpenAI",
    needsApiKey: true, needsBaseUrl: false,
    presets: ["gpt-4o", "gpt-4o-mini", "o3-mini", "o1"],
    defaultModel: "gpt-4o",
  },
  ollama: {
    id: "ollama", label: "Ollama (本地)",
    needsApiKey: false, needsBaseUrl: true,
    presets: ["llama3", "mistral", "qwen2.5", "gemma2"],
    defaultModel: "llama3",
  },
  gemini: {
    id: "gemini", label: "Google Gemini",
    needsApiKey: true, needsBaseUrl: false,
    presets: ["gemini-2.5-flash", "gemini-2.5-pro"],
    defaultModel: "gemini-2.5-flash",
  },
  deepseek: {
    id: "deepseek", label: "DeepSeek",
    needsApiKey: true, needsBaseUrl: false,
    presets: ["deepseek-chat", "deepseek-reasoner"],
    defaultModel: "deepseek-chat",
  },
  custom: {
    id: "custom", label: "自定义 (OpenAI 兼容)",
    needsApiKey: true, needsBaseUrl: true,
    presets: [],
    defaultModel: "",
  },
};

/* ------------------------------------------------------------------ */
/*  Form state — the editable subset of ConfigMap + the (never       */
/*  pre-filled) api_key field.                                         */
/* ------------------------------------------------------------------ */

interface ConfigFormState {
  llm_provider: string;
  api_key: string;        // user-typed value; empty means "keep existing"
  base_url: string;
  model: string;
  host: string;
  port: string;
}

function buildFormState(cfg: ConfigMap): ConfigFormState {
  return {
    llm_provider: cfg.llm_provider,
    api_key: "",            // never pre-fill raw key
    base_url: cfg.base_url,
    model: cfg.model,
    host: cfg.host,
    port: cfg.port,
  };
}

export default function ConfigPage() {
  const { data: config, isLoading } = useConfig();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-16">
        <Loader2 className="size-6 animate-spin" style={{ color: "var(--accent-base)" }} />
      </div>
    );
  }

  if (!config) {
    return (
      <div className="p-8">
        <p style={{ color: "var(--text-tertiary)" }}>加载配置失败。请检查后端服务是否正常运行。</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl p-8">
      <div className="mb-10 flex items-end justify-between">
        <div>
          <span
            className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[0.7rem] font-medium tracking-wide"
            style={{ background: "var(--accent-subtle)", color: "var(--accent-text)" }}
          >
            <Wrench className="size-3" />
            配置
          </span>
          <h1 className="mt-2 text-3xl font-bold tracking-tight" style={{ color: "var(--text-primary)" }}>
            应用配置
          </h1>
          <p className="mt-1.5 text-sm" style={{ color: "var(--text-tertiary)" }}>
            应用和 LLM 设置
          </p>
        </div>
      </div>

      <ConfigFields initialConfig={config} />
    </div>
  );
}

function ConfigFields({ initialConfig }: { initialConfig: ConfigMap }) {
  const save = useSaveConfig();
  const [form, setForm] = useState<ConfigFormState>(buildFormState(initialConfig));
  const [manualModel, setManualModel] = useState(false);

  const provider = form.llm_provider?.toLowerCase() || "claude";
  const providerInfo = PROVIDERS[provider];

  // Fetch models dynamically when provider/apiKey/baseUrl change.
  // The api_key typed by the user is sent to /fetch-models so the
  // backend can call the provider's models endpoint on their behalf.
  const { data: remoteModels, isFetching: modelsLoading, refetch: refetchModels } =
    useFetchModels(provider, form.api_key, form.base_url);

  const models = remoteModels ?? providerInfo?.presets ?? [];

  // Whether to show a text input instead of the model selector
  const isCustomModel = manualModel || (form.model && models.length > 0 && !models.includes(form.model));

  const handleChange = <K extends keyof ConfigFormState>(key: K, value: ConfigFormState[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleSave = () => {
    // Ensure model is not empty before saving
    const model = form.model || providerInfo?.defaultModel || "";

    // Build the save payload: only include api_key if the user typed
    // something. An empty field means "keep the existing key" so the
    // user's previously stored secret is preserved.
    const payload: ConfigSaveInput = {
      llm_provider: form.llm_provider,
      base_url: form.base_url,
      model,
      host: form.host,
      port: form.port,
    };
    if (form.api_key.trim() !== "") {
      payload.api_key = form.api_key;
    }

    save.mutate(payload, {
      onSuccess: () => {
        // Clear the api_key field after a successful save so the
        // password isn't left sitting in the form.
        setForm((prev) => ({ ...prev, api_key: "" }));
      },
    });
  };

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      {/* LLM settings */}
      <Card surface="solid">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">LLM 连接</CardTitle>
            <Button size="sm" onClick={handleSave} disabled={save.isPending}>
              <Save className="size-4" />
              {save.isPending ? "保存中..." : "保存"}
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-5">
          {/* Provider */}
          <div className="space-y-2">
            <label className="text-sm font-medium" style={{ color: "var(--text-secondary)" }}>
              LLM 提供商
            </label>
            <Select
              value={provider}
              onValueChange={(v) => {
                if (!v) return;
                const info = PROVIDERS[v];
                setManualModel(false);
                setForm((prev) => ({
                  ...prev,
                  llm_provider: v,
                  model: info?.defaultModel ?? "",
                  // Clear fields that are no longer needed
                  ...(info?.needsApiKey ? {} : { api_key: "" }),
                  ...(info?.needsBaseUrl ? {} : { base_url: "" }),
                }));
              }}
            >
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(PROVIDERS).map(([id, info]) => (
                  <SelectItem key={id} value={id}>
                    {info.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* API Key */}
          {providerInfo?.needsApiKey && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium" style={{ color: "var(--text-secondary)" }}>
                  {provider === "custom" ? "API Key" : `${providerInfo.label} API Key`}
                </label>
                <ApiKeyStatusBadge
                  isSet={initialConfig.api_key_set}
                  masked={initialConfig.api_key_masked}
                />
              </div>
              <Input
                value={form.api_key}
                onChange={(e) => handleChange("api_key", e.target.value)}
                type="password"
                placeholder={
                  initialConfig.api_key_set
                    ? "输入新 API Key 覆盖现有值..."
                    : "输入 API Key..."
                }
                autoComplete="off"
              />
              {initialConfig.api_key_set && initialConfig.api_key_masked && (
                <p className="flex items-center gap-1 text-xs" style={{ color: "var(--text-tertiary)" }}>
                  <KeyRound className="size-3" />
                  当前 Key: <code style={{ color: "var(--text-secondary)" }}>{initialConfig.api_key_masked}</code>
                  <span>（保存时若留空则保留原 Key）</span>
                </p>
              )}
            </div>
          )}

          {/* Base URL */}
          {providerInfo?.needsBaseUrl && (
            <div className="space-y-2">
              <label className="text-sm font-medium" style={{ color: "var(--text-secondary)" }}>
                {providerInfo.label} API 地址
              </label>
              <Input
                value={form.base_url}
                onChange={(e) => handleChange("base_url", e.target.value)}
                placeholder={
                  provider === "ollama"
                    ? "http://localhost:11434"
                    : provider === "custom"
                    ? "https://api.example.com/v1"
                    : undefined
                }
              />
            </div>
          )}

          {/* Model */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium" style={{ color: "var(--text-secondary)" }}>
                模型
              </label>
              <div className="flex items-center gap-2">
                {isCustomModel && (
                  <button
                    className="text-xs underline"
                    style={{ color: "var(--text-tertiary)" }}
                    onClick={() => {
                      setManualModel(false);
                      setForm((prev) => ({ ...prev, model: models[0] ?? "" }));
                    }}
                  >
                    从列表选择
                  </button>
                )}
                <button
                  className="flex items-center gap-1 text-xs"
                  style={{ color: "var(--text-muted)" }}
                  onClick={() => refetchModels()}
                  disabled={modelsLoading}
                >
                  <RefreshCw className={`size-3 ${modelsLoading ? "animate-spin" : ""}`} />
                  刷新
                </button>
              </div>
            </div>

            {isCustomModel ? (
              <Input
                value={form.model}
                onChange={(e) => handleChange("model", e.target.value)}
                placeholder="输入模型名称..."
              />
            ) : (
              <Select
                value={form.model}
                onValueChange={(v) => {
                  if (!v) return;
                  if (v === "__manual__") {
                    setManualModel(true);
                  } else {
                    setManualModel(false);
                    handleChange("model", v);
                  }
                }}
              >
                <SelectTrigger className="w-full">
                  <SelectValue placeholder={modelsLoading ? "加载中..." : "选择模型"} />
                </SelectTrigger>
                <SelectContent>
                  {models.length > 0 && (
                    <>
                      {models.map((m) => (
                        <SelectItem key={m} value={m}>
                          {m}
                        </SelectItem>
                      ))}
                      <div className="my-1 h-px" style={{ background: "var(--border-subtle)" }} />
                    </>
                  )}
                  <SelectItem value="__manual__">✏️ 手动输入...</SelectItem>
                </SelectContent>
              </Select>
            )}

            {modelsLoading && (
              <p className="flex items-center gap-1 text-xs" style={{ color: "var(--text-tertiary)" }}>
                <Loader2 className="size-3 animate-spin" />
                获取模型中...
              </p>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Server settings */}
      <Card surface="solid">
        <CardHeader>
          <CardTitle className="text-base">服务器</CardTitle>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="space-y-2">
            <label className="text-sm font-medium" style={{ color: "var(--text-secondary)" }}>
              监听地址
            </label>
            <Input
              value={form.host}
              onChange={(e) => handleChange("host", e.target.value)}
              placeholder="0.0.0.0"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium" style={{ color: "var(--text-secondary)" }}>
              端口
            </label>
            <Input
              value={form.port}
              onChange={(e) => handleChange("port", e.target.value)}
              placeholder="8000"
            />
          </div>
          <div
            className="rounded-lg border p-3 text-xs leading-relaxed"
            style={{
              background: "var(--bg-elevated)",
              borderColor: "var(--border-subtle)",
              color: "var(--text-tertiary)",
            }}
          >
            修改主机和端口后需要重启服务端才能生效。
          </div>
        </CardContent>
      </Card>

      {save.data && (
        <div className="lg:col-span-2">
          <p className="text-sm" style={{ color: "var(--success-text)" }}>
            配置已保存。
          </p>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Small badge showing whether an api_key is already set              */
/* ------------------------------------------------------------------ */

function ApiKeyStatusBadge({ isSet, masked }: { isSet: boolean; masked: string }) {
  if (isSet) {
    return (
      <span
        className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[0.7rem] font-medium"
        style={{ background: "var(--success-subtle)", color: "var(--success-text)" }}
        title={masked}
      >
        <CheckCircle2 className="size-3" />
        Key 已设置
      </span>
    );
  }
  return (
    <span
      className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[0.7rem] font-medium"
      style={{ background: "var(--warning-subtle)", color: "var(--warning-text)" }}
    >
      <AlertCircle className="size-3" />
      未设置
    </span>
  );
}
