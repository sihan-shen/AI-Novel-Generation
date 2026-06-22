import { useQuery } from "@tanstack/react-query";
import { api, unwrap } from "@/lib/api-client";
import { createMutationHooks } from "./factory";

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

export interface ChapterCreate {
  title: string;
  project_id: string;
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

/* ---- mutation hooks (factory-generated) ---- */

const factory = createMutationHooks<Chapter, ChapterCreate>(
  "chapters",
  chapterKeys.all,
);

export const useCreateChapter = factory.useCreate;
export const useUpdateChapter = factory.useUpdate;
export const useDeleteChapter = factory.useDelete;
