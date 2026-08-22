/**
 * Centralized endpoint paths + base-URL reader.
 *
 * Why a dedicated module?
 *   - One source of truth for the API base URL.
 *   - Components import paths from here, never hard-code "http://localhost:8000".
 *   - Tests can mock this single module instead of `process.env`.
 *
 * Backend prefix note: the FastAPI routers are mounted under `/api/v1`,
 * so every call resolves to `{API_BASE}/{API_VERSION}/auth`, `.../documents`, etc.
 */

const DEFAULT_API_URL = "http://localhost:8000";
const DEFAULT_API_VERSION = "/api/v1";

export const API_BASE_URL: string =
  process.env.NEXT_PUBLIC_API_URL ?? DEFAULT_API_URL;

export const API_VERSION: string =
  process.env.NEXT_PUBLIC_API_VERSION ?? DEFAULT_API_VERSION;

export const API_ROOT: string = `${API_BASE_URL}${API_VERSION}`;

export const API_PATHS = {
  auth: {
    register: "/auth/register",
    login: "/auth/login",
    me: "/auth/me",
  },
  documents: {
    list: "/documents",
    upload: "/documents/upload",
    byId: (id: string) => `/documents/${id}`,
  },
  courses: {
    list: "/courses",
    byId: (id: string) => `/courses/${id}`,
  },
  search: "/search",
  chat: {
    oneShot: "/chat",
    sessions: "/chat/sessions",
    sessionById: (id: string) => `/chat/sessions/${id}`,
    sendMessage: (id: string) => `/chat/sessions/${id}/messages`,
  },
} as const;
