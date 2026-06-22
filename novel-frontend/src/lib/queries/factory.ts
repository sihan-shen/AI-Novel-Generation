import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "@/lib/api-client";

/**
 * Factory that creates standardized create/update/delete mutation hooks
 * for a CRUD resource.
 *
 * @param resourceName  URL segment (e.g. "settings", "outlines", "chapters")
 * @param keyFactory    Query-key factory for cache invalidation
 * @returns `{ useCreate, useUpdate, useDelete }` hook functions
 */
export function createMutationHooks<
  TResult,
  TCreate = TResult,
>(
  resourceName: string,
  keyFactory: (projectId: string) => readonly string[],
) {
  const useCreate = (projectId: string) => {
    const client = useQueryClient();
    return useMutation({
      mutationFn: (data: TCreate) =>
        api
          .post(`projects/${projectId}/${resourceName}`, { json: data })
          .then(unwrap<TResult>),
      onSuccess: () =>
        client.invalidateQueries({ queryKey: keyFactory(projectId) }),
      onError: (error: Error) =>
        console.error(`[${resourceName}] create failed:`, error),
    });
  };

  const useUpdate = (projectId: string) => {
    const client = useQueryClient();
    return useMutation({
      mutationFn: ({ id, data }: { id: string; data: Partial<TResult> }) =>
        api
          .put(`projects/${projectId}/${resourceName}/${id}`, { json: data })
          .then(unwrap<TResult>),
      onSuccess: () =>
        client.invalidateQueries({ queryKey: keyFactory(projectId) }),
      onError: (error: Error) =>
        console.error(`[${resourceName}] update failed:`, error),
    });
  };

  const useDelete = (projectId: string) => {
    const client = useQueryClient();
    return useMutation({
      mutationFn: (id: string) =>
        api
          .delete(`projects/${projectId}/${resourceName}/${id}`)
          .then(unwrap<{ deleted: string }>),
      onSuccess: () =>
        client.invalidateQueries({ queryKey: keyFactory(projectId) }),
      onError: (error: Error) =>
        console.error(`[${resourceName}] delete failed:`, error),
    });
  };

  return { useCreate, useUpdate, useDelete };
}
