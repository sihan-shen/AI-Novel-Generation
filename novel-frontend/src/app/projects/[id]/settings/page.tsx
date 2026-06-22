"use client";

import { useParams } from "next/navigation";
import { useState } from "react";
import {
  useSettings,
  useCreateSetting,
  useUpdateSetting,
  useDeleteSetting,
} from "@/lib/queries/settings";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Plus, Trash2, Loader2, Edit3 } from "lucide-react";

const CATEGORIES = [
  "全部",
  "人物",
  "世界观",
  "组织",
  "地理",
  "体系",
  "事件",
  "物品",
];

export default function SettingsPage() {
  const { id: projectId } = useParams<{ id: string }>();
  const [category, setCategory] = useState<string | null>(null);
  const [openCreate, setOpenCreate] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);

  const { data: settings, isLoading } = useSettings(
    projectId,
    category === "全部" ? null : category,
  );
  const create = useCreateSetting(projectId);
  const update = useUpdateSetting(projectId);
  const remove = useDeleteSetting(projectId);

  /* ── create form state ── */
  const [formCategory, setFormCategory] = useState("人物");
  const [formName, setFormName] = useState("");
  const [formSummary, setFormSummary] = useState("");
  const [formContent, setFormContent] = useState("");

  /* ── inline edit state ── */
  const [editName, setEditName] = useState("");
  const [editSummary, setEditSummary] = useState("");

  const handleCreate = async () => {
    if (!formName.trim()) return;
    await create.mutateAsync({
      project_id: projectId,
      category: formCategory,
      name: formName,
      summary: formSummary,
      content: formContent,
    });
    setFormName("");
    setFormSummary("");
    setFormContent("");
    setOpenCreate(false);
  };

  const handleUpdate = async (id: string) => {
    await update.mutateAsync({
      id,
      data: { name: editName, summary: editSummary },
    });
    setEditingId(null);
  };

  const startEdit = (s: { id: string; name: string; summary: string }) => {
    setEditingId(s.id);
    setEditName(s.name);
    setEditSummary(s.summary);
  };

  return (
    <div className="p-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">设定集</h1>
          <p className="mt-1 text-sm text-muted-foreground">人物、世界观、组织等设定条目</p>
        </div>
        <Dialog open={openCreate} onOpenChange={setOpenCreate}>
          <DialogTrigger className="inline-flex items-center gap-2 rounded-md bg-secondary text-secondary-foreground hover:bg-muted px-3 py-1.5 text-sm font-medium transition-colors">
            <Plus className="size-4" />
            新建
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>新建设定条目</DialogTitle>
            </DialogHeader>
            <div className="space-y-3">
              <Select value={formCategory} onValueChange={(v) => v && setFormCategory(v)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CATEGORIES.filter((c) => c !== "全部").map((c) => (
                    <SelectItem key={c} value={c}>
                      {c}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Input
                placeholder="名称"
                value={formName}
                onChange={(e) => setFormName(e.target.value)}
              />
              <Input
                placeholder="摘要（可选）"
                value={formSummary}
                onChange={(e) => setFormSummary(e.target.value)}
              />
              <textarea
                className="min-h-24 w-full rounded-md border px-3 py-2 text-sm"
                placeholder="详细内容（可选）"
                value={formContent}
                onChange={(e) => setFormContent(e.target.value)}
              />
              <Button
                className="w-full"
                onClick={handleCreate}
                disabled={create.isPending}
              >
                创建
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* Category tabs */}
      <div className="mt-4 flex gap-1 overflow-x-auto">
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            onClick={() => setCategory(cat === "全部" ? null : cat)}
            className={`rounded-md px-3 py-1.5 text-sm transition-colors ${
              (cat === "全部" && !category) || cat === category
                ? "bg-secondary font-medium text-secondary-foreground"
                : "text-muted-foreground hover:bg-muted"
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="mt-16 flex justify-center">
          <Loader2 className="size-6 animate-spin" style={{ color: "var(--text-muted)" }} />
        </div>
      ) : (
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {settings?.map((s) => (
            <Card key={s.id} className="group relative">
              <CardHeader>
                {editingId === s.id ? (
                  <div className="space-y-2">
                    <Input
                      value={editName}
                      onChange={(e) => setEditName(e.target.value)}
                      className="font-semibold"
                    />
                    <Input
                      value={editSummary}
                      onChange={(e) => setEditSummary(e.target.value)}
                    />
                    <div className="flex gap-2">
                      <Button size="sm" onClick={() => handleUpdate(s.id)}>
                        保存
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setEditingId(null)}
                      >
                        取消
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div>
                    <CardTitle className="flex items-center gap-2 text-base">
                      {s.name}
                      <button
                        className="rounded p-0.5 opacity-0 transition-opacity hover:bg-muted group-hover:opacity-100"
                        onClick={() => startEdit(s)}
                      >
                        <Edit3 className="size-3" style={{ color: "var(--text-muted)" }} />
                      </button>
                    </CardTitle>
                    <span className="text-xs" style={{ color: "var(--text-muted)" }}>{s.category}</span>
                  </div>
                )}
              </CardHeader>
              {editingId !== s.id && s.summary && (
                <CardContent>
                  <p className="line-clamp-2 text-sm text-muted-foreground">{s.summary}</p>
                </CardContent>
              )}
              <button
                className="absolute right-2 top-2 rounded p-1 opacity-0 hover:bg-red-50 group-hover:opacity-100"
                onClick={() => remove.mutate(s.id)}
              >
                <Trash2 className="size-3.5 text-red-500" />
              </button>
            </Card>
          ))}
        </div>
      )}

      {!isLoading && settings?.length === 0 && (
        <p className="mt-16 text-center" style={{ color: "var(--text-muted)" }}>
          还没有设定条目，创建一个吧。
        </p>
      )}
    </div>
  );
}
