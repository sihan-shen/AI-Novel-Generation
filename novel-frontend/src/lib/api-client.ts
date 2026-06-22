/** HTTP client for backend API communication. */

import ky from "ky";

/* ------------------------------------------------------------------ */
/*  ky instance                                                        */
/* ------------------------------------------------------------------ */

export const api = ky.create({
  prefix: "/api",
  hooks: {
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
