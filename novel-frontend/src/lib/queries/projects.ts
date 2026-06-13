import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "@/lib/api-client";

/* ------------------------------------------------------------------ */
/*  Types (matching backend schemas)                                   */
/* ------------------------------------------------------------------ */

export interface Project {
  id: string;
  title: string;
  description: string;
  genre: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface ProjectCreate {
  title: string;
  description?: string;
  genre?: string;
}

/* ------------------------------------------------------------------ */
/*  Query keys                                                        */
/* ------------------------------------------------------------------ */

export const projectKeys = {
  all: ["projects"] as const,
  detail: (id: string) => ["projects", id] as const,
};

/* ------------------------------------------------------------------ */
/*  Hooks                                                             */
/* ------------------------------------------------------------------ */

export function useProjects() {
  return useQuery({
    queryKey: projectKeys.all,
    queryFn: () => api.get("projects").then(unwrap<Project[]>),
  });
}

export function useProject(id: string) {
  return useQuery({
    queryKey: projectKeys.detail(id),
    queryFn: () => api.get(`projects/${id}`).then(unwrap<Project>),
    enabled: !!id,
  });
}

export function useCreateProject() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (data: ProjectCreate) =>
      api.post("projects", { json: data }).then(unwrap<Project>),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: projectKeys.all });
    },
  });
}

export function useDeleteProject() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api.delete(`projects/${id}`).then(unwrap<{ deleted: string }>),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: projectKeys.all });
    },
  });
}
