/**
 * Thin typed client for the LaariLaara API (FastAPI backend in ../backend).
 *
 * Errors follow RFC 9457 problem+json with a stable machine-readable `code`
 * (see backend/app/core/errors.py). A generated OpenAPI client can replace
 * the hand-rolled types later; this wrapper's surface is deliberately small.
 */

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export const IS_LOCAL_API = /^https?:\/\/(?:localhost|127\.0\.0\.1)(?::|\/|$)/i.test(
  API_BASE_URL,
);

/** RFC 9457 problem+json body produced by the backend. */
export interface Problem {
  type: string;
  title: string;
  status: number;
  code: string;
  detail?: string;
  instance?: string;
  requestId?: string;
  errors?: Array<{ field?: string; message?: string }>;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly problem: Problem | null;

  constructor(status: number, problem: Problem | null) {
    super(problem?.detail ?? problem?.title ?? `API error ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.code = problem?.code ?? "UNKNOWN";
    this.problem = problem;
  }
}

let accessToken: string | null = null;

/** Set (or clear) the bearer token attached to subsequent requests. */
export function setAccessToken(token: string | null) {
  accessToken = token;
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;

  const res = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    let problem: Problem | null = null;
    try {
      problem = (await res.json()) as Problem;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, problem);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body),
  put: <T>(path: string, body?: unknown) => request<T>("PUT", path, body),
  patch: <T>(path: string, body?: unknown) => request<T>("PATCH", path, body),
  delete: <T>(path: string) => request<T>("DELETE", path),
};
