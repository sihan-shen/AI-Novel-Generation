/** HTTP client and auth provider for backend API communication. */

import ky from "ky";

/* ------------------------------------------------------------------ */
/*  Auth provider interface                                            */
/* ------------------------------------------------------------------ */

interface AuthProvider {
  getHeaders(): Record<string, string>;
}

/** Phase 1: no authentication (identical to current backend behavior). */
class NoAuthProvider implements AuthProvider {
  getHeaders(): Record<string, string> {
    return {};
  }
}

/** Phase 2+ API-key provider (for lan/tailscale exposure). */
class ApiKeyProvider implements AuthProvider {
  constructor(private apiKey: string) {}
  getHeaders(): Record<string, string> {
    return { "X-API-Key": this.apiKey };
  }
}

let authProvider: AuthProvider = new NoAuthProvider();

export function setAuthProvider(provider: AuthProvider) {
  authProvider = provider;
}

export function useApiKey(key: string) {
  authProvider = new ApiKeyProvider(key);
}

/* ------------------------------------------------------------------ */
/*  ky instance                                                        */
/* ------------------------------------------------------------------ */

export const api = ky.create({
  prefix: "/api",
  hooks: {
    beforeRequest: [
      ({ request }) => {
        const headers = authProvider.getHeaders();
        for (const [key, value] of Object.entries(headers)) {
          request.headers.set(key, value);
        }
      },
    ],
    afterResponse: [
      async (_state) => {
        const { response } = _state;
        if (!response.ok) {
          const body = await response.json().catch(() => ({}));
          const detail =
            (body as { detail?: string }).detail ?? response.statusText;
          throw new ApiError(response.status, detail);
        }
      },
    ],
  },
});

/* ------------------------------------------------------------------ */
/*  Error type                                                         */
/* ------------------------------------------------------------------ */

export class ApiError extends Error {
  constructor(
    public status: number,
    detail: string,
  ) {
    super(detail);
    this.name = "ApiError";
  }
}

/* ------------------------------------------------------------------ */
/*  Typed response helpers                                             */
/* ------------------------------------------------------------------ */

/** An APIResponse envelope from the backend. */
export interface APIResponse<T> {
  data: T;
  message: string;
}

/** Unwrap the data portion of an APIResponse. */
export async function unwrap<T>(response: Response): Promise<T> {
  const body = (await response.json()) as APIResponse<T>;
  return body.data;
}
