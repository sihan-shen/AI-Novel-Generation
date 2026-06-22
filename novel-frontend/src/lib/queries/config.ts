import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "@/lib/api-client";

/* ------------------------------------------------------------------ */
/*  Types (matching backend /api/config response)                      */
/*                                                                     */
/*  GET returns a redacted view: the raw api_key is replaced by        */
/*  api_key_set (bool) + api_key_masked (string, e.g. "sk-...6789").  */
/*  All other fields are strings.                                      */
/* ------------------------------------------------------------------ */

export interface ConfigMap {
  llm_provider: string;
  base_url: string;
  model: string;
  host: string;
  port: string;
  api_key_set: boolean;
  api_key_masked: string;
}

/** Body accepted by POST /api/config. The server still accepts the
 *  raw api_key here (it is then stored, and the response is masked). */
export interface ConfigSaveInput {
  llm_provider?: string;
  api_key?: string;
  base_url?: string;
  model?: string;
  host?: string;
  port?: string;
}

export const configKeys = {
  all: ["config"] as const,
  models: (provider: string) => ["config", "models", provider] as const,
};

export function useConfig() {
  return useQuery({
    queryKey: configKeys.all,
    queryFn: () => api.get("config").then(unwrap<ConfigMap>),
  });
}

export function useSaveConfig() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (data: ConfigSaveInput) =>
      api.post("config", { json: data }).then(unwrap<ConfigMap>),
    onSuccess: () => client.invalidateQueries({ queryKey: configKeys.all }),
  });
}

export function useFetchModels(provider: string, apiKey: string, baseUrl: string) {
  return useQuery({
    queryKey: configKeys.models(provider),
    queryFn: async () => {
      const params = new URLSearchParams({ provider });
      if (apiKey) params.set("api_key", apiKey);
      if (baseUrl) params.set("base_url", baseUrl);
      const res = await api.get(`config/fetch-models?${params}`);
      const body = await res.json<{ data: { models: string[] }; message: string }>();
      return body.data.models;
    },
    enabled: !!provider,
    staleTime: 60_000,
    retry: false,
  });
}
