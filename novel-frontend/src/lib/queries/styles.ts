import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "@/lib/api-client";

export interface Style {
  id: string;
  name: string;
  source: string;
  source_text: string;
  analysis: string;
  created_at: string;
  updated_at: string;
}

export const styleKeys = {
  all: ["styles"] as const,
};

export function useStyles() {
  return useQuery({
    queryKey: styleKeys.all,
    queryFn: () => api.get("styles").then(unwrap<Style[]>),
  });
}

export function useDeleteStyle() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete(`styles/${id}`),
    onSuccess: () => client.invalidateQueries({ queryKey: styleKeys.all }),
  });
}
