import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "@/lib/api-client";

export interface Chapter {
  id: string;
  project_id: string;
  outline_id: string | null;
  title: string;
  content: string;
  status: string;
  sort_order: number;
  notes: string;
  word_count: number;
  created_at: string;
  updated_at: string;
}

export const chapterKeys = {
  all: (projectId: string) => ["chapters", projectId] as const,
};

export function useChapters(projectId: string) {
  return useQuery({
    queryKey: chapterKeys.all(projectId),
    queryFn: () =>
      api.get(`projects/${projectId}/chapters`).then(unwrap<Chapter[]>),
    enabled: !!projectId,
  });
}

export function useCreateChapter(projectId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (data: { title: string; project_id: string }) =>
      api
        .post(`projects/${projectId}/chapters`, { json: data })
        .then(unwrap<Chapter>),
    onSuccess: () =>
      client.invalidateQueries({ queryKey: chapterKeys.all(projectId) }),
  });
}

export function useUpdateChapter(projectId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Chapter> }) =>
      api
        .put(`projects/${projectId}/chapters/${id}`, { json: data })
        .then(unwrap<Chapter>),
    onSuccess: () =>
      client.invalidateQueries({ queryKey: chapterKeys.all(projectId) }),
  });
}

export function useDeleteChapter(projectId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api.delete(`projects/${projectId}/chapters/${id}`),
    onSuccess: () =>
      client.invalidateQueries({ queryKey: chapterKeys.all(projectId) }),
  });
}
