import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "@/lib/api-client";

export interface Outline {
  id: string;
  project_id: string;
  parent_id: string | null;
  level: number;
  sort_order: number;
  title: string;
  summary: string;
  notes: string;
  status: string;
  word_count_target: number;
  word_count_actual: number;
  pov_character: string;
  created_at: string;
  updated_at: string;
  children: Outline[];
}

export const outlineKeys = {
  tree: (projectId: string) => ["outlines", projectId] as const,
};

export function useOutlineTree(projectId: string) {
  return useQuery({
    queryKey: outlineKeys.tree(projectId),
    queryFn: () =>
      api.get(`projects/${projectId}/outlines`).then(unwrap<Outline[]>),
    enabled: !!projectId,
  });
}

export function useCreateOutline(projectId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (data: {
      project_id: string;
      level?: number;
      parent_id?: string | null;
      title: string;
      summary?: string;
    }) =>
      api
        .post(`projects/${projectId}/outlines`, { json: data })
        .then(unwrap<Outline>),
    onSuccess: () =>
      client.invalidateQueries({ queryKey: outlineKeys.tree(projectId) }),
  });
}

export function useUpdateOutline(projectId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Outline> }) =>
      api
        .put(`projects/${projectId}/outlines/${id}`, { json: data })
        .then(unwrap<Outline>),
    onSuccess: () =>
      client.invalidateQueries({ queryKey: outlineKeys.tree(projectId) }),
  });
}

export function useDeleteOutline(projectId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api.delete(`projects/${projectId}/outlines/${id}`),
    onSuccess: () =>
      client.invalidateQueries({ queryKey: outlineKeys.tree(projectId) }),
  });
}
