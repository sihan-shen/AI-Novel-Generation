import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "@/lib/api-client";

export type ConfigMap = Record<string, string>;

export const configKeys = {
  all: ["config"] as const,
};

export function useConfig() {
  return useQuery({
    queryKey: configKeys.all,
    queryFn: () => api.get("config").then((r) => r.json<{ data: ConfigMap; message: string }>().then((b) => b.data)),
  });
}

export function useSaveConfig() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<ConfigMap>) =>
      api.post("config", { json: data }).then((r) => r.json<{ data: ConfigMap }>().then((b) => b.data)),
    onSuccess: () => client.invalidateQueries({ queryKey: configKeys.all }),
  });
}
