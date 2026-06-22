import { useQuery } from "@tanstack/react-query";
import { api, unwrap } from "@/lib/api-client";
import { createMutationHooks } from "./factory";

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

export interface OutlineCreate {
  project_id: string;
  level?: number;
  parent_id?: string | null;
  title: string;
  summary?: string;
}

export const outlineKeys = {
  all: (projectId: string) => ["outlines", projectId] as const,
};

export function useOutlineTree(projectId: string) {
  return useQuery({
    queryKey: outlineKeys.all(projectId),
    queryFn: () =>
      api.get(`projects/${projectId}/outlines`).then(unwrap<Outline[]>),
    enabled: !!projectId,
  });
}

/* ---- mutation hooks (factory-generated) ---- */

const factory = createMutationHooks<Outline, OutlineCreate>(
  "outlines",
  outlineKeys.all,
);

export const useCreateOutline = factory.useCreate;
export const useUpdateOutline = factory.useUpdate;
export const useDeleteOutline = factory.useDelete;
