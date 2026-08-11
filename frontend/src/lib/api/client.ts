import { API_ROOT, API_PATHS } from "@/lib/constants/api";
import { APIError, type APIErrorPayload, type NoContent } from "@/types/api";

interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  /** Required if the backend will stream a multipart payload. */
  formData?: FormData;
  /** When true, sends `Authorization: Bearer <token>` from storage if present. */
  auth?: boolean;
  /** Aborts the fetch. */
  signal?: AbortSignal;
}

/**
 * Resolve an API_PATHS entry — accepts either a string or a path-builder function.
 */
function resolvePath(path: string | ((...args: never[]) => string)): string {
  return typeof path === "string" ? path : path();
}

function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem("academicos:auth:token");
}

async function readError(response: Response): Promise<APIError> {
  let payload: APIErrorPayload | undefined;
  try {
    payload = (await response.json()) as APIErrorPayload;
  } catch {
    payload = undefined;
  }
  const detail = payload?.detail;
  const message =
    typeof detail === "string"
      ? detail
      : Array.isArray(detail)
        ? detail.map((d) => d.msg).join("; ")
        : `Request failed with status ${response.status}`;
  return new APIError(message, response.status, payload);
}

/**
 * Send a typed request to the backend.
 *
 * - Prefixes every path with `API_ROOT` (the FastAPI base + version).
 * - JSON-encodes `body` and sets the content-type automatically.
 * - When `formData` is set, sends it as multipart (Content-Type auto-set).
 * - When `auth !== false`, attaches `Authorization: Bearer ...` if a token exists.
 * - Throws `APIError` for any non-2xx response.
 * - Returns `null` for 204 responses.
 */
export async function apiFetch<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { method = "GET", body, formData, auth = true, signal } = options;
  const url = `${API_ROOT}${resolvePath(path as never)}`;

  const headers: Record<string, string> = { Accept: "application/json" };

  let payload: BodyInit | undefined;
  if (formData) {
    payload = formData; // browser sets multipart boundary
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  if (auth) {
    const token = getAccessToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(url, {
    method,
    headers,
    body: payload,
    signal,
  });

  if (res.status === 204) return undefined as unknown as T;
  if (!res.ok) throw await readError(res);

  // Some endpoints may return empty 200s. Guard.
  const text = await res.text();
  if (!text) return undefined as unknown as T;
  return JSON.parse(text) as T;
}

/** Convenience: typed re-export of API path map so call sites don't import it twice. */
export { API_PATHS };
export type { NoContent };
