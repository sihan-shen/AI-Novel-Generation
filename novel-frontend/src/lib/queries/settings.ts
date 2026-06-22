import { useQuery } from "@tanstack/react-query";
import { api, unwrap } from "@/lib/api-client";
import { createMutationHooks } from "./factory";

export interface Setting {
  id: string;
  project_id: string;
  category: string;
  name: string;
  summary: string;
  content: string;
  weight: number;
  status: string;
  tags: string;
  created_at: string;
  updated_at: string;
}

export interface SettingCreate {
  project_id: string;
  category: string;
  name: string;
  summary?: string;
  content?: string;
  weight?: number;
}

export const settingKeys = {
  all: (projectId: string) => ["settings", projectId] as const,
  byCategory: (projectId: string, category?: string) =>
    ["settings", projectId, category] as const,
};

export function useSettings(projectId: string, category?: string | null) {
  const params = category ? `?category=${encodeURIComponent(category)}` : "";
  return useQuery({
    queryKey: settingKeys.byCategory(projectId, category ?? undefined),
    queryFn: () =>
      api.get(`projects/${projectId}/settings${params}`).then(unwrap<Setting[]>),
    enabled: !!projectId,
  });
}

/* ---- mutation hooks (factory-generated) ---- */

const factory = createMutationHooks<Setting, SettingCreate>(
  "settings",
  settingKeys.all,
);

export const useCreateSetting = factory.useCreate;
export const useUpdateSetting = factory.useUpdate;
export const useDeleteSetting = factory.useDelete;
