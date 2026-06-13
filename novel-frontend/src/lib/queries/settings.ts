import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "@/lib/api-client";

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

export function useCreateSetting(projectId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (data: SettingCreate) =>
      api
        .post(`projects/${projectId}/settings`, { json: { ...data, project_id: projectId } })
        .then(unwrap<Setting>),
    onSuccess: () =>
      client.invalidateQueries({ queryKey: settingKeys.all(projectId) }),
  });
}

export function useUpdateSetting(projectId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Setting> }) =>
      api
        .put(`projects/${projectId}/settings/${id}`, { json: data })
        .then(unwrap<Setting>),
    onSuccess: () =>
      client.invalidateQueries({ queryKey: settingKeys.all(projectId) }),
  });
}

export function useDeleteSetting(projectId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api.delete(`projects/${projectId}/settings/${id}`),
    onSuccess: () =>
      client.invalidateQueries({ queryKey: settingKeys.all(projectId) }),
  });
}
