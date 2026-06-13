import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "@/lib/api-client";

export interface Idea {
  id: string;
  project_id: string | null;
  title: string;
  content: string;
  source: string;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export const ideaKeys = {
  all: ["ideas"] as const,
};

export function useIdeas(projectId?: string | null) {
  return useQuery({
    queryKey: [...ideaKeys.all, projectId],
    queryFn: () => {
      const search = projectId ? `?project_id=${projectId}` : "";
      return api.get(`ideas${search}`).then(unwrap<Idea[]>);
    },
  });
}

export function useCreateIdea() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (data: { title: string; content?: string; source?: string; project_id?: string | null }) =>
      api.post("ideas", { json: data }).then(unwrap<Idea>),
    onSuccess: () => client.invalidateQueries({ queryKey: ideaKeys.all }),
  });
}

export function useDeleteIdea() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete(`ideas/${id}`),
    onSuccess: () => client.invalidateQueries({ queryKey: ideaKeys.all }),
  });
}
