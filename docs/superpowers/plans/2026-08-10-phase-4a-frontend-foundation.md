# Phase 4A — Frontend Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish a clean, production-quality frontend foundation for AcademicOS — design system, dark theme, typed API client, auth architecture, app shell, responsive primitives — without building feature pages.

**Architecture:**
- App Router (Next.js 16) with route groups `(auth)` and `(app)`.
- Styling: CSS Modules + CSS custom-property tokens (no Tailwind, no UI kit). One source of truth in `src/app/globals.css`.
- API: central `src/lib/api/client.ts` with typed domain modules (`auth`, `documents`, `chat`, `search`) sharing one bearer-token-aware fetch wrapper. No `fetch()` scattered through components.
- Auth: JWT in `localStorage` (matches existing backend's stateless bearer design). React Context provider exposes `{ user, accessToken, login, register, logout, refresh-user }`. Route protection via a server-agnostic client guard (since this is currently a fully-client-rendered shell — no middleware yet).
- State: React only. No Redux / Zustand. Auth is the only app-wide state; everything else lives in component state.
- Types: `src/types/` derived directly from backend Pydantic schemas (no field invention).

**Tech Stack:**
- Next.js `16.3.0` (App Router)
- React `19.2.8`
- TypeScript `5.x` (strict)
- ESLint flat config (`eslint-config-next` + `@next/eslint-plugin-next`)
- Reticle `@reticlehq/next` + `@reticlehq/react` (already wired; preserved as-is)
- **No Tailwind, no UI library** — design tokens in CSS variables, components hand-built.

## Global Constraints

- Next.js 16.3.0: APIs and conventions differ from training data. Read `node_modules/next/dist/docs/` before writing code in `src/app/`.
- Reticle must remain dev-only. The `ReticleDev` component must keep a `NODE_ENV === "development"` guard, and `@reticlehq/next`'s `withReticle` wrapper must remain in `next.config.ts` (it's a prod no-op).
- `JWT` only ever lives in `localStorage` under the key `academicos:auth`. Never in a cookie that the server implicitly sends — the existing backend is bearer-only.
- All values exposed to the browser MUST be prefixed `NEXT_PUBLIC_`. Backend secrets (GEMINI, DB, QDRANT, SECRET_KEY) must NEVER appear in `frontend/.env*`.
- `npm run lint`, `npx tsc --noEmit`, and `npm run build` must all pass before Phase 4A is declared complete.
- Backend test suite must remain `164+ passed / 0 failed`.
- `frontend/.env*` are gitignored. `.env.example` is the only env file committed.

---

## File Structure (target end of Phase 4A)

```
frontend/
├── next.config.ts                              (modify: add serverActions config only if needed; otherwise unchanged)
├── next-env.d.ts                               (auto, untouched)
├── package.json                                (modify: add lint, typecheck scripts)
├── eslint.config.mjs                           (NEW: flat config)
├── .env.example                                (NEW)
├── tsconfig.json                               (modify: ensure strict + path alias)
├── AGENTS.md                                   (untouched)
├── CLAUDE.md                                   (untouched)
├── public/                                     (untouched; only deleted SVGs matter in gitignore)
├── src/
│   ├── app/
│   │   ├── layout.tsx                          (modify: dark theme + tokens + AppShell)
│   │   ├── page.tsx                            (rewrite: marketing/landing page that demonstrates shell)
│   │   ├── globals.css                         (rewrite: design tokens + dark-first theme)
│   │   ├── reticle-dev.tsx                     (unchanged — already correct)
│   │   └── favicon.ico                         (untouched)
│   ├── components/
│   │   ├── layout/
│   │   │   ├── AppShell.tsx                    (NEW)
│   │   │   ├── Sidebar.tsx                     (NEW)
│   │   │   ├── TopBar.tsx                      (NEW)
│   │   │   └── PageContainer.tsx               (NEW)
│   │   ├── primitives/
│   │   │   ├── LoadingState.tsx                (NEW)
│   │   │   ├── ErrorState.tsx                 (NEW)
│   │   │   └── EmptyState.tsx                 (NEW)
│   │   └── ui/
│   │       ├── Button.tsx                      (NEW)
│   │       ├── Logo.tsx                        (NEW)
│   │       └── ThemeProvider.tsx               (NEW — guards dark/light color scheme; ships dark)
│   ├── lib/
│   │   ├── api/
│   │   │   ├── client.ts                       (NEW: typed fetch wrapper)
│   │   │   ├── auth.ts                         (NEW)
│   │   │   ├── documents.ts                    (NEW)
│   │   │   ├── chat.ts                         (NEW)
│   │   │   └── search.ts                       (NEW)
│   │   ├── auth/
│   │   │   ├── storage.ts                      (NEW: localStorage access with SSR-safe guards)
│   │   │   └── guards.ts                       (NEW: client-side route guards)
│   │   ├── hooks/
│   │   │   └── useAuth.ts                      (NEW: context consumer hook)
│   │   ├── context/
│   │   │   └── AuthContext.tsx                 (NEW: provider + types)
│   │   ├── constants/
│   │   │   └── api.ts                          (NEW: endpoint paths + API base URL reader)
│   │   └── utils/
│   │       └── cn.ts                           (NEW: tiny className merger — used across UI)
│   └── types/
│       ├── user.ts                             (NEW)
│       ├── document.ts                         (NEW)
│       ├── chat.ts                             (NEW)
│       ├── search.ts                           (NEW)
│       ├── api.ts                              (NEW: APIError + common envelopes)
│       └── index.ts                            (NEW: barrel)
```

---

## Task 1: Baseline checks and environment documentation

**Files:**
- Create: `frontend/.env.example`
- Modify: `frontend/.gitignore` (already covers `.env*`; verify)
- Test: `backend/.` — run `pytest` to capture current pass count

- [ ] **Step 1.1: Run backend tests to capture pre-Phase-4A baseline**

Run: `cd backend && pytest -q 2>&1 | tail -5`
Expected: `164 passed`. Record exact number — Phase 4A must not regress it.

- [ ] **Step 1.2: Confirm frontend builds before any change**

Run: `cd frontend && npm run build 2>&1 | tail -20`
Expected: Clean production build of the existing scaffold. If it fails, STOP — debug before proceeding.

- [ ] **Step 1.3: Create `.env.example`**

Create file `frontend/.env.example`:

```text
# AcademicOS frontend env (publicly-exposed only — no secrets here).
# Copy to .env.local for local dev.
#
# Backend base URL for all REST calls. The browser makes these requests
# directly; CORS must be enabled on the FastAPI backend for this origin.
NEXT_PUBLIC_API_URL=http://localhost:8000

# API version prefix used by every call. Matches the FastAPI router prefix.
NEXT_PUBLIC_API_VERSION=/api/v1

# Optional. Reticle dev-bridge pairing token. Leave blank in dev for solo work.
# NEXT_PUBLIC_RETICLE_TOKEN=
```

- [ ] **Step 1.4: Verify `.env` is gitignored**

Read `frontend/.gitignore`. Confirm the `.env*` line is present. If absent, add `.env` and `.env.local` (do NOT add `.env.example` — it should remain tracked).

- [ ] **Step 1.5: Commit**

```bash
git add frontend/.env.example backend/.gitignore frontend/.gitignore
git commit -m "chore(frontend): add .env.example and verify gitignore"
```

---

## Task 2: TypeScript types from backend contracts

**Files:**
- Create: `frontend/src/types/api.ts`
- Create: `frontend/src/types/user.ts`
- Create: `frontend/src/types/document.ts`
- Create: `frontend/src/types/chat.ts`
- Create: `frontend/src/types/search.ts`
- Create: `frontend/src/types/index.ts`

**Interfaces:**
- Consumes: nothing
- Produces: A single import path `@/types` for all backend contract types.

Field-level guidance (derive from backend code — DO NOT invent fields):
- `User` → `UserResponse` in `backend/app/schemas/user.py:63-72`
- `Document` → `DocumentResponse` in `backend/app/schemas/document.py:51-59`
- `DocumentUploadStatus` → enum in `backend/app/db/models/enums.py:19-25`
- `ChatRole` → enum in `backend/app/db/models/enums.py:29-32`
- `ChatSession` → `ChatSessionResponse` in `backend/app/schemas/chat.py:48-56`
- `ChatMessage` → `ChatMessageResponse` in `backend/app/schemas/chat.py:74-82`
- `ChatMessageSource` → `ChatMessageSourceResponse` in `backend/app/schemas/chat.py:93-106`
- `ChatSessionWithMessages` → `ChatSessionWithMessagesResponse` in `backend/app/schemas/chat.py:112-115`
- `ChatRequest` / `ChatResponse` → `backend/app/schemas/chat.py:121-191`
- `SendMessageRequest` / `SendMessageResponse` → `backend/app/schemas/chat.py:196-256`
- `ChatSource` → `backend/app/schemas/chat.py:169-179`
- `SearchRequest` / `SearchResponse` / `RetrievedChunk` → `backend/app/schemas/search.py:7-50`
- `LoginRequest` → `backend/app/schemas/auth.py:19-34`
- `TokenResponse` → `backend/app/schemas/auth.py:37-41`
- `APIError` → normalize `FastAPI`'s `{ detail: string | array }` shape plus HTTP status (own type below)

- [ ] **Step 2.1: Create `src/types/api.ts`**

```ts
// API-level envelopes + the normalized error shape used across the app.

export interface APIErrorPayload {
  /** Human-readable message from the backend. May be a list for 422. */
  detail: string | Array<{ loc?: Array<string | number>; msg: string; type?: string }>;
}

export class APIError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly payload?: APIErrorPayload,
  ) {
    super(message);
    this.name = "APIError";
  }
}

/** 204 / void response. */
export type NoContent = void;

/** Common list-pagination shape used by `?skip=&limit=` endpoints. */
export interface PageParams {
  skip?: number;
  limit?: number;
}
```

- [ ] **Step 2.2: Create `src/types/user.ts`**

```ts
import type { UUID } from "@/types/api";

export interface User {
  id: UUID;
  full_name: string;
  email: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string; // ISO-8601 from datetime
  updated_at: string;
}

export interface RegisterPayload {
  full_name: string;
  email: string;
  password: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: "bearer";
}

export type { UUID };
```

(Re-export `UUID` once from `api.ts`; consumers import from `@/types/user` for convenience.) Adjust the file order in Step 2.6's barrel accordingly.

- [ ] **Step 2.3: Create `src/types/document.ts`**

```ts
import type { UUID } from "@/types/api";

export type DocumentUploadStatus = "pending" | "uploading" | "processing" | "ready" | "failed";

export interface Document {
  id: UUID;
  owner_id: UUID;
  filename: string;
  original_filename: string;
  file_type: string;
  file_size: number;
  storage_path: string;
  upload_status: DocumentUploadStatus;
  created_at: string;
  updated_at: string;
}
```

- [ ] **Step 2.4: Create `src/types/chat.ts`**

```ts
import type { UUID } from "@/types/api";

export type ChatRole = "user" | "assistant" | "system";
export type RetrievalMode = "semantic" | "hybrid";

export interface ChatMessageSource {
  id: UUID;
  message_id: UUID;
  document_id: UUID;
  chunk_id: string;
  position: number;
  page_number?: number | null;
  slide_number?: number | null;
  score?: number | null;
  snippet?: string | null;
}

export interface ChatMessage {
  id: UUID;
  session_id: UUID;
  role: ChatRole;
  content: string;
  created_at: string;
}

export interface ChatMessageWithSources extends ChatMessage {
  sources: ChatMessageSource[];
}

export interface ChatSession {
  id: UUID;
  user_id: UUID;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ChatSessionWithMessages extends ChatSession {
  messages: ChatMessageWithSources[];
}

export interface ChatSource {
  index: number;
  chunk_id: string;
  document_id?: UUID | null;
  document_title?: string | null;
  page_number?: number | null;
  chunk_index: number;
  score: number;
  snippet: string;
}

export interface ChatRequest {
  query: string;
  document_id?: UUID | null;
  mode?: RetrievalMode;
  top_k?: number;
  score_threshold?: number | null;
  temperature?: number;
  max_output_tokens?: number;
}

export interface ChatResponse {
  answer: string;
  sources: ChatSource[];
  model: string;
  retrieval_mode: RetrievalMode;
  prompt_tokens?: number | null;
  completion_tokens?: number | null;
}

export interface SendMessagePayload {
  query: string;
  document_id?: UUID | null;
  mode?: RetrievalMode;
  top_k?: number;
  score_threshold?: number | null;
  temperature?: number;
  max_output_tokens?: number;
}

export interface SendMessageResponse {
  user_message: ChatMessage;
  assistant_message: ChatMessageWithSources;
  model: string;
  retrieval_mode: RetrievalMode;
  prompt_tokens?: number | null;
  completion_tokens?: number | null;
}

export interface CreateSessionPayload {
  title?: string;
  initial_query?: string;
}

export interface UpdateSessionPayload {
  title?: string;
}
```

- [ ] **Step 2.5: Create `src/types/search.ts`**

```ts
import type { UUID } from "@/types/api";
import type { RetrievalMode } from "@/types/chat";

export interface RetrievedChunk {
  chunk_id: string;
  document_id?: UUID | null;
  text: string;
  score: number;
  page_number?: number | null;
  chunk_index: number;
  metadata: Record<string, unknown>;
}

export interface SearchRequest {
  query: string;
  top_k?: number;
  score_threshold?: number | null;
  document_id?: UUID | null;
  mode?: RetrievalMode;
}

export interface SearchResponse {
  results: RetrievedChunk[];
}
```

- [ ] **Step 2.6: Create `src/types/index.ts` (barrel)**

```ts
export * from "./api";
export * from "./user";
export * from "./document";
export * from "./chat";
export * from "./search";
```

Note: `UUID` is declared in `api.ts` (change Step 2.2 to import `UUID` from `./api` rather than re-declare):

```ts
// src/types/user.ts (revised)
import type { UUID } from "./api";
// ... rest unchanged
```

- [ ] **Step 2.7: Verify compilation**

Run: `cd frontend && npx tsc --noEmit 2>&1 | tail -20`
Expected: Zero errors. (Note: `tsconfig` include currently pulls every `.ts/.tsx`, so any stray file would also be checked.)

- [ ] **Step 2.8: Commit**

```bash
git add frontend/src/types
git commit -m "feat(types): add backend-derived TypeScript contracts"
```

---

## Task 3: API constants and tiny utility

**Files:**
- Create: `frontend/src/lib/constants/api.ts`
- Create: `frontend/src/lib/utils/cn.ts`

- [ ] **Step 3.1: Create `src/lib/constants/api.ts`**

```ts
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
  search: "/search",
  chat: {
    oneShot: "/chat",
    sessions: "/chat/sessions",
    sessionById: (id: string) => `/chat/sessions/${id}`,
    sendMessage: (id: string) => `/chat/sessions/${id}/messages`,
  },
} as const;
```

- [ ] **Step 3.2: Create `src/lib/utils/cn.ts`**

```ts
/**
 * Tiny className merger.
 *
 * Not clsx — keeps the dependency surface at zero. Filters falsy values so
 * callers can write `cn("base", isActive && "active", className)`.
 */
export type ClassValue = string | number | false | null | undefined;

export function cn(...values: ClassValue[]): string {
  return values.filter(Boolean).join(" ");
}
```

- [ ] **Step 3.3: Commit**

```bash
git add frontend/src/lib/constants frontend/src/lib/utils
git commit -m "feat(lib): centralize API constants + className helper"
```

---

## Task 4: Central typed API client

**Files:**
- Create: `frontend/src/lib/api/client.ts`

**Interfaces:**
- Consumes: `@/types`, `@/lib/constants/api`, `@/lib/auth/storage` (Task 5)
- Produces: `apiFetch<T>(path, init?)` — every other API module uses this.

Backend auth contract (from `app/api/deps.py` and `app/api/v1/endpoints/auth.py`):
- Login / register return `TokenResponse` (`{ access_token, token_type: "bearer" }`).
- Protected endpoints expect `Authorization: Bearer <access_token>`.

- [ ] **Step 4.1: Create `src/lib/api/client.ts`**

```ts
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
```

- [ ] **Step 4.2: Commit**

```bash
git add frontend/src/lib/api/client.ts
git commit -m "feat(api): central typed fetch wrapper with bearer + error normalization"
```

---

## Task 5: Auth storage helpers

**Files:**
- Create: `frontend/src/lib/auth/storage.ts`

**Interfaces:**
- Consumes: nothing
- Produces: `getStoredToken()`, `setStoredToken(token)`, `clearStoredToken()`.

SSR-safety rationale: `localStorage` is browser-only. Helpers short-circuit on the server (Next.js sometimes renders server components that touch this code transitively). Token itself never leaves the browser.

- [ ] **Step 5.1: Create `src/lib/auth/storage.ts`**

```ts
/**
 * Token storage.
 *
 * Why localStorage and not a cookie?
 *   - Backend is stateless bearer-only. Cookies would imply CSRF + a server
 *     in the loop. The browser handles auth directly, which keeps the shell
 *     deployable as a fully static export if we want that later.
 *
 * Key choice `academicos:auth:token` is namespaced so we can add more keys
 * (e.g., `academicos:auth:user`) without colliding with libraries.
 *
 * No refresh token yet — backend does not issue one.
 */

const TOKEN_KEY = "academicos:auth:token";
const USER_KEY = "academicos:auth:user";

function hasStorage(): boolean {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

export function getStoredToken(): string | null {
  return hasStorage() ? window.localStorage.getItem(TOKEN_KEY) : null;
}

export function setStoredToken(token: string): void {
  if (!hasStorage()) return;
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearStoredAuth(): void {
  if (!hasStorage()) return;
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(USER_KEY);
}

export function getStoredUserJSON<T>(): T | null {
  if (!hasStorage()) return null;
  const raw = window.localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

export function setStoredUserJSON<T>(user: T): void {
  if (!hasStorage()) return;
  window.localStorage.setItem(USER_KEY, JSON.stringify(user));
}
```

- [ ] **Step 5.2: Commit**

```bash
git add frontend/src/lib/auth/storage.ts
git commit -m "feat(auth): localStorage helpers for token + cached user"
```

---

## Task 6: Domain API modules

**Files:**
- Create: `frontend/src/lib/api/auth.ts`
- Create: `frontend/src/lib/api/documents.ts`
- Create: `frontend/src/lib/api/chat.ts`
- Create: `frontend/src/lib/api/search.ts`

**Interfaces:**
- Consumes: `@/lib/api/client`, `@/types`
- Produces: One namespace per backend resource group.

- [ ] **Step 6.1: Create `src/lib/api/auth.ts`**

```ts
import { apiFetch, API_PATHS } from "./client";
import type { LoginPayload, RegisterPayload, TokenResponse, User } from "@/types";

export const authApi = {
  register: (payload: RegisterPayload) =>
    apiFetch<User>(API_PATHS.auth.register, { method: "POST", body: payload, auth: false }),

  login: (payload: LoginPayload) =>
    apiFetch<TokenResponse>(API_PATHS.auth.login, { method: "POST", body: payload, auth: false }),

  me: () => apiFetch<User>(API_PATHS.auth.me),
};
```

- [ ] **Step 6.2: Create `src/lib/api/documents.ts`**

```ts
import { apiFetch, API_PATHS } from "./client";
import type { Document, PageParams } from "@/types";

export const documentsApi = {
  list: (params?: PageParams) => {
    const search = new URLSearchParams();
    if (params?.skip !== undefined) search.set("skip", String(params.skip));
    if (params?.limit !== undefined) search.set("limit", String(params.limit));
    const qs = search.toString();
    return apiFetch<Document[]>(`${API_PATHS.documents.list}${qs ? `?${qs}` : ""}`);
  },

  upload: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return apiFetch<Document>(API_PATHS.documents.upload, {
      method: "POST",
      formData,
    });
  },

  get: (id: string) => apiFetch<Document>(API_PATHS.documents.byId(id)),

  remove: (id: string) =>
    apiFetch<void>(API_PATHS.documents.byId(id), { method: "DELETE" }),
};
```

- [ ] **Step 6.3: Create `src/lib/api/chat.ts`**

```ts
import { apiFetch, API_PATHS } from "./client";
import type {
  ChatResponse,
  ChatSession,
  ChatSessionWithMessages,
  CreateSessionPayload,
  SendMessagePayload,
  SendMessageResponse,
  UpdateSessionPayload,
  Void,
} from "@/types";

// Re-export `void` under the local name Void for call-site clarity; the
// underlying type lives in `@/types` and is `void`.
type _Void = Void;

export const chatApi = {
  oneShot: (payload: import("@/types").ChatRequest) =>
    apiFetch<ChatResponse>(API_PATHS.chat.oneShot, { method: "POST", body: payload }),

  createSession: (payload: CreateSessionPayload) =>
    apiFetch<ChatSession>(API_PATHS.chat.sessions, { method: "POST", body: payload }),

  listSessions: () => apiFetch<ChatSession[]>(API_PATHS.chat.sessions),

  getSession: (id: string) => apiFetch<ChatSessionWithMessages>(API_PATHS.chat.sessionById(id)),

  updateSession: (id: string, payload: UpdateSessionPayload) =>
    apiFetch<ChatSession>(API_PATHS.chat.sessionById(id), { method: "PATCH", body: payload }),

  deleteSession: (id: string) =>
    apiFetch<_Void>(API_PATHS.chat.sessionById(id), { method: "DELETE" }),

  sendMessage: (id: string, payload: SendMessagePayload) =>
    apiFetch<SendMessageResponse>(API_PATHS.chat.sendMessage(id), {
      method: "POST",
      body: payload,
    }),
};
```

> Note on `Void`: Add the following to `src/types/api.ts` (refining Step 2.1):

```ts
export type Void = void;
```

(Drop the explicit underscore alias in `chat.ts` and just use `void` — simpler.)

- [ ] **Step 6.4: Create `src/lib/api/search.ts`**

```ts
import { apiFetch, API_PATHS } from "./client";
import type { SearchRequest, SearchResponse } from "@/types";

export const searchApi = {
  search: (payload: SearchRequest) =>
    apiFetch<SearchResponse>(API_PATHS.search, { method: "POST", body: payload }),
};
```

- [ ] **Step 6.5: Commit**

```bash
git add frontend/src/lib/api
git commit -m "feat(api): typed domain modules for auth, documents, chat, search"
```

---

## Task 7: Auth context + provider + hook

**Files:**
- Create: `frontend/src/lib/context/AuthContext.tsx`
- Create: `frontend/src/lib/hooks/useAuth.ts`

**Interfaces:**
- Consumes: `@/lib/api/auth`, `@/lib/auth/storage`, `@/types`
- Produces:
  - `<AuthProvider>` — top-level client provider
  - `useAuth()` — `{ user, status, login, register, logout, refreshUser }`
  - `status`: `"loading" | "authenticated" | "unauthenticated"`

- [ ] **Step 7.1: Create `src/lib/context/AuthContext.tsx`**

```tsx
"use client";

import {
  createContext,
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { authApi } from "@/lib/api/auth";
import {
  clearStoredAuth,
  getStoredToken,
  getStoredUserJSON,
  setStoredToken,
  setStoredUserJSON,
} from "@/lib/auth/storage";
import type { LoginPayload, RegisterPayload, User } from "@/types";

export type AuthStatus = "loading" | "authenticated" | "unauthenticated";

export interface AuthContextValue {
  status: AuthStatus;
  user: User | null;
  accessToken: string | null;
  login(payload: LoginPayload): Promise<void>;
  register(payload: RegisterPayload): Promise<void>;
  logout(): void;
  refreshUser(): Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

interface ProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: ProviderProps) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<User | null>(null);

  // Bootstrap: if a token exists, validate it by calling /me.
  useEffect(() => {
    let cancelled = false;
    async function bootstrap() {
      const token = getStoredToken();
      if (!token) {
        if (!cancelled) setStatus("unauthenticated");
        return;
      }
      try {
        const fresh = await authApi.me();
        if (cancelled) return;
        setUser(fresh);
        setStoredUserJSON(fresh);
        setStatus("authenticated");
      } catch {
        // Token invalid/expired — drop it.
        clearStoredAuth();
        setStatus("unauthenticated");
      }
    }
    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (payload: LoginPayload) => {
    const token = await authApi.login(payload);
    setStoredToken(token.access_token);
    const fresh = await authApi.me();
    setUser(fresh);
    setStoredUserJSON(fresh);
    setStatus("authenticated");
  }, []);

  const register = useCallback(async (payload: RegisterPayload) => {
    await authApi.register(payload);
    await login({ email: payload.email, password: payload.password });
  }, [login]);

  const refreshUser = useCallback(async () => {
    const fresh = await authApi.me();
    setUser(fresh);
    setStoredUserJSON(fresh);
  }, []);

  const logout = useCallback(() => {
    clearStoredAuth();
    setUser(null);
    setStatus("unauthenticated");
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user,
      accessToken: getStoredToken(),
      login,
      register,
      logout,
      refreshUser,
    }),
    [status, user, login, register, logout, refreshUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
```

- [ ] **Step 7.2: Create `src/lib/hooks/useAuth.ts`**

```ts
"use client";

import { useContext } from "react";
import { AuthContext, type AuthContextValue } from "@/lib/context/AuthContext";

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside <AuthProvider>");
  }
  return ctx;
}
```

- [ ] **Step 7.3: Commit**

```bash
git add frontend/src/lib/context frontend/src/lib/hooks
git commit -m "feat(auth): context provider + useAuth hook with bootstrap"
```

---

## Task 8: Route guards

**Files:**
- Create: `frontend/src/lib/auth/guards.ts`

**Interfaces:**
- Consumes: `useAuth`
- Produces: `RequireAuth` and `RedirectIfAuthed` client components.

- [ ] **Step 8.1: Create `src/lib/auth/guards.tsx`**

```tsx
"use client";

import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";
import { useAuth } from "@/lib/hooks/useAuth";

interface Props {
  children: ReactNode;
}

/** Client-side guard for protected routes. */
export function RequireAuth({ children }: Props) {
  const { status } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/login");
    }
  }, [status, router]);

  if (status === "loading" || status === "unauthenticated") {
    // Render nothing — keeps the layout stable, avoids flicker.
    return null;
  }
  return <>{children}</>;
}

/** Inverse guard: redirect authenticated users away from /login, /register. */
export function RedirectIfAuthed({ children }: Props) {
  const { status } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (status === "authenticated") {
      router.replace("/dashboard");
    }
  }, [status, router]);

  if (status === "loading" || status === "authenticated") return null;
  return <>{children}</>;
}
```

> File extension: this file uses JSX, so save it as `frontend/src/lib/auth/guards.tsx` rather than `.ts`.

- [ ] **Step 8.2: Commit**

```bash
git add frontend/src/lib/auth/guards.tsx
git commit -m "feat(auth): client route guards (RequireAuth, RedirectIfAuthed)"
```

---

## Task 9: Design tokens (global CSS, dark-first theme)

**Files:**
- Modify: `frontend/src/app/globals.css`

Goal: One source of truth for all colors, spacing, radii, typography. Dark is the canonical state; `prefers-color-scheme: light` is allowed but dark stays primary. All later UI consumes `var(--...)` tokens — never raw hex values.

- [ ] **Step 9.1: Replace `src/app/globals.css`**

```css
/* ---------------------------------------------------------------------------
   AcademicOS — design tokens & global styles.
   Single source of truth. Every component reads from these vars.
   --------------------------------------------------------------------------- */

:root {
  color-scheme: dark;

  /* Surfaces (dark-first; lighter values swappable via prefers-color-scheme) */
  --bg-canvas: #07090d;
  --bg-surface: #0d1117;
  --bg-surface-muted: #131923;
  --bg-elevated: #1a2230;
  --bg-overlay: rgba(7, 9, 13, 0.72);

  /* Borders + dividers */
  --border-subtle: #1f2733;
  --border-strong: #2d3845;

  /* Text hierarchy */
  --fg-primary: #e6edf3;
  --fg-secondary: #9aa6b2;
  --fg-tertiary: #6b7785;
  --fg-disabled: #444c56;

  /* Foreground on accent */
  --fg-on-primary: #07090d;

  /* Accent (calm, technical — not neon) */
  --accent: #6aa3ff;
  --accent-hover: #80b1ff;
  --accent-active: #5187e8;
  --accent-muted: rgba(106, 163, 255, 0.12);

  /* Semantic */
  --success: #57c08f;
  --warning: #e0a458;
  --danger: #e06b6b;

  /* Sizing */
  --radius-xs: 4px;
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 14px;
  --radius-xl: 20px;

  /* Spacing scale (4-px base; matches Tailwind spacing roughly) */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;
  --space-12: 48px;
  --space-16: 64px;

  /* Typography */
  --font-sans: var(--font-geist-sans), -apple-system, BlinkMacSystemFont, "Segoe UI",
    Roboto, "Helvetica Neue", Arial, sans-serif;
  --font-mono: var(--font-geist-mono), ui-monospace, SFMono-Regular, Menlo,
    Monaco, Consolas, monospace;

  --text-xs: 12px;
  --text-sm: 14px;
  --text-base: 16px;
  --text-lg: 18px;
  --text-xl: 22px;
  --text-2xl: 28px;
  --text-3xl: 36px;

  --leading-tight: 1.2;
  --leading-snug: 1.4;
  --leading-normal: 1.55;
  --leading-relaxed: 1.7;

  /* Effects */
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.4);
  --shadow-md: 0 6px 18px rgba(0, 0, 0, 0.45);
  --shadow-lg: 0 18px 40px rgba(0, 0, 0, 0.55);

  --focus-ring: 0 0 0 2px var(--bg-canvas), 0 0 0 4px var(--accent);
  --transition-fast: 120ms ease;
  --transition-base: 200ms ease;
}

/* Optional light scheme — kept as a courtesy. App ships dark. */
@media (prefers-color-scheme: light) {
  :root {
    color-scheme: light;
    --bg-canvas: #f7f8fa;
    --bg-surface: #ffffff;
    --bg-surface-muted: #f1f3f6;
    --bg-elevated: #ffffff;
    --bg-overlay: rgba(255, 255, 255, 0.72);

    --border-subtle: #e5e8ec;
    --border-strong: #cdd3da;

    --fg-primary: #0a0f14;
    --fg-secondary: #4b5563;
    --fg-tertiary: #6b7280;
    --fg-disabled: #b3b8bf;

    --fg-on-primary: #ffffff;

    --accent: #2c5fd9;
    --accent-hover: #3b6fe0;
    --accent-active: #214cba;
    --accent-muted: rgba(44, 95, 217, 0.12);
  }
}

/* Reset + base */
*,
*::before,
*::after {
  box-sizing: border-box;
}

html,
body {
  padding: 0;
  margin: 0;
  max-width: 100vw;
  overflow-x: hidden;
}

html {
  height: 100%;
  -webkit-text-size-adjust: 100%;
}

body {
  min-height: 100%;
  font-family: var(--font-sans);
  font-size: var(--text-base);
  line-height: var(--leading-normal);
  color: var(--fg-primary);
  background: var(--bg-canvas);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* Links */
a {
  color: var(--accent);
  text-decoration: none;
  transition: color var(--transition-fast);
}
a:hover {
  color: var(--accent-hover);
}

/* Focus visibility — never lose keyboard users. */
:focus-visible {
  outline: none;
  box-shadow: var(--focus-ring);
  border-radius: var(--radius-sm);
}

/* Buttons get browser defaults reset by app-level components; here we just make sure
   form controls inherit the right font. */
button,
input,
select,
textarea {
  font: inherit;
  color: inherit;
}

/* Selection */
::selection {
  background: var(--accent-muted);
  color: var(--fg-primary);
}
```

- [ ] **Step 9.2: Commit**

```bash
git add frontend/src/app/globals.css
git commit -m "feat(design): dark-first token system + global resets"
```

---

## Task 10: Reusable UI primitives — Button + Logo

**Files:**
- Create: `frontend/src/components/ui/Logo.tsx` (+ `Logo.module.css`)
- Create: `frontend/src/components/ui/Button.tsx` (+ `Button.module.css`)

- [ ] **Step 10.1: Create `Logo.module.css`**

```css
.logo {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--fg-primary);
  font-family: var(--font-sans);
  font-weight: 600;
  letter-spacing: -0.01em;
}

.mark {
  width: 28px;
  height: 28px;
  border-radius: var(--radius-sm);
  background: linear-gradient(140deg, var(--accent), var(--accent-active));
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--fg-on-primary);
  font-weight: 700;
  font-size: 13px;
  letter-spacing: 0.04em;
}

.wordmark {
  font-size: var(--text-lg);
}
```

- [ ] **Step 10.2: Create `Logo.tsx`**

```tsx
import styles from "./Logo.module.css";

interface Props {
  size?: "sm" | "md";
  showWordmark?: boolean;
}

export function Logo({ size = "md", showWordmark = true }: Props) {
  const dim = size === "sm" ? 22 : 28;
  return (
    <span className={styles.logo} data-testid="logo">
      <span className={styles.mark} style={{ width: dim, height: dim }}>
        AO
      </span>
      {showWordmark && <span className={styles.wordmark}>AcademicOS</span>}
    </span>
  );
}
```

- [ ] **Step 10.3: Create `Button.module.css`**

```css
.button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: 0 var(--space-4);
  height: 38px;
  border-radius: var(--radius-md);
  border: 1px solid transparent;
  font-weight: 500;
  font-size: var(--text-sm);
  cursor: pointer;
  transition:
    background var(--transition-fast),
    border-color var(--transition-fast),
    color var(--transition-fast);
  user-select: none;
}

.button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.primary {
  background: var(--accent);
  color: var(--fg-on-primary);
}
.primary:hover:not(:disabled) {
  background: var(--accent-hover);
}
.primary:active:not(:disabled) {
  background: var(--accent-active);
}

.secondary {
  background: var(--bg-surface-muted);
  color: var(--fg-primary);
  border-color: var(--border-subtle);
}
.secondary:hover:not(:disabled) {
  background: var(--bg-elevated);
  border-color: var(--border-strong);
}

.ghost {
  background: transparent;
  color: var(--fg-secondary);
}
.ghost:hover:not(:disabled) {
  background: var(--accent-muted);
  color: var(--fg-primary);
}

.danger {
  background: var(--danger);
  color: var(--fg-on-primary);
}

.fullWidth {
  width: 100%;
}
```

- [ ] **Step 10.4: Create `Button.tsx`**

```tsx
"use client";

import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/utils/cn";
import styles from "./Button.module.css";

type Variant = "primary" | "secondary" | "ghost" | "danger";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  fullWidth?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = "primary", fullWidth, className, type = "button", ...rest }, ref) => (
    <button
      ref={ref}
      type={type}
      className={cn(styles.button, styles[variant], fullWidth && styles.fullWidth, className)}
      {...rest}
    />
  ),
);

Button.displayName = "Button";
```

- [ ] **Step 10.5: Commit**

```bash
git add frontend/src/components/ui
git commit -m "feat(ui): Logo + Button primitives on top of design tokens"
```

---

## Task 11: State primitives — Loading/Error/Empty

**Files:**
- Create: `frontend/src/components/primitives/LoadingState.tsx` (+ `.module.css`)
- Create: `frontend/src/components/primitives/ErrorState.tsx` (+ `.module.css`)
- Create: `frontend/src/components/primitives/EmptyState.tsx` (+ `.module.css`)

- [ ] **Step 11.1: Create `LoadingState.tsx`**

```tsx
import styles from "./LoadingState.module.css";

interface Props {
  label?: string;
}

export function LoadingState({ label = "Loading…" }: Props) {
  return (
    <div role="status" aria-live="polite" className={styles.root}>
      <span className={styles.spinner} aria-hidden="true" />
      <span className={styles.label}>{label}</span>
    </div>
  );
}
```

```css
/* LoadingState.module.css */
.root {
  display: inline-flex;
  align-items: center;
  gap: var(--space-3);
  color: var(--fg-secondary);
  padding: var(--space-6);
  font-size: var(--text-sm);
}

.spinner {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 2px solid var(--border-subtle);
  border-top-color: var(--accent);
  animation: spin 700ms linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.label {
  letter-spacing: 0.01em;
}
```

- [ ] **Step 11.2: Create `ErrorState.tsx`**

```tsx
import styles from "./ErrorState.module.css";

interface Props {
  title?: string;
  description?: string;
}

export function ErrorState({
  title = "Something went wrong",
  description = "Please try again in a moment.",
}: Props) {
  return (
    <div role="alert" className={styles.root}>
      <div className={styles.title}>{title}</div>
      <div className={styles.description}>{description}</div>
    </div>
  );
}
```

```css
/* ErrorState.module.css */
.root {
  border: 1px solid var(--border-subtle);
  background: var(--bg-surface);
  border-radius: var(--radius-md);
  padding: var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.title {
  color: var(--danger);
  font-weight: 600;
  font-size: var(--text-base);
}

.description {
  color: var(--fg-secondary);
  font-size: var(--text-sm);
}
```

- [ ] **Step 11.3: Create `EmptyState.tsx`**

```tsx
import type { ReactNode } from "react";
import styles from "./EmptyState.module.css";

interface Props {
  title: string;
  description?: string;
  action?: ReactNode;
}

export function EmptyState({ title, description, action }: Props) {
  return (
    <div className={styles.root}>
      <div className={styles.title}>{title}</div>
      {description ? <div className={styles.description}>{description}</div> : null}
      {action ? <div className={styles.action}>{action}</div> : null}
    </div>
  );
}
```

```css
/* EmptyState.module.css */
.root {
  border: 1px dashed var(--border-subtle);
  background: var(--bg-surface);
  border-radius: var(--radius-md);
  padding: var(--space-8);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  align-items: center;
  text-align: center;
}

.title {
  color: var(--fg-primary);
  font-weight: 600;
  font-size: var(--text-lg);
}

.description {
  color: var(--fg-secondary);
  font-size: var(--text-sm);
  max-width: 36ch;
}

.action {
  margin-top: var(--space-2);
}
```

- [ ] **Step 11.4: Commit**

```bash
git add frontend/src/components/primitives
git commit -m "feat(primitives): generic Loading/Error/Empty states"
```

---

## Task 12: Application shell — Sidebar, TopBar, AppShell, PageContainer

**Files:**
- Create: `frontend/src/components/layout/Sidebar.tsx` (+ `Sidebar.module.css`)
- Create: `frontend/src/components/layout/TopBar.tsx` (+ `TopBar.module.css`)
- Create: `frontend/src/components/layout/AppShell.tsx` (+ `AppShell.module.css`)
- Create: `frontend/src/components/layout/PageContainer.tsx` (+ `PageContainer.module.css`)

Goals:
- AppShell establishes `<aside> sidebar | <header> topbar | <main> content`.
- Responsive: sidebar collapses to a slide-in drawer on `< 900px`. The collapse is structural (not animated) — accessible via a real button.
- No fake data. Sidebar links point to route groups that exist or will exist (`/dashboard`, `/documents`, `/chat`). Page modules for them are NOT built in Phase 4A; they will land in 4B/C/D/E. Sidebar links remain present-but-inert (they navigate; the page modules will be added).
- The shell handles `aria-current` and proper button vs. link semantics.

- [ ] **Step 12.1: Create `Sidebar.module.css`**

```css
.sidebar {
  width: 240px;
  flex-shrink: 0;
  background: var(--bg-surface);
  border-right: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  padding: var(--space-4);
  gap: var(--space-4);
  position: sticky;
  top: 0;
  height: 100vh;
}

.brand {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2);
}

.nav {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.section {
  text-transform: uppercase;
  font-size: var(--text-xs);
  letter-spacing: 0.08em;
  color: var(--fg-tertiary);
  padding: var(--space-3) var(--space-2) var(--space-1);
}

.link {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3);
  border-radius: var(--radius-md);
  color: var(--fg-secondary);
  font-size: var(--text-sm);
  font-weight: 500;
  transition:
    background var(--transition-fast),
    color var(--transition-fast);
}
.link:hover {
  background: var(--bg-surface-muted);
  color: var(--fg-primary);
}
.linkActive {
  background: var(--accent-muted);
  color: var(--fg-primary);
}

.footer {
  margin-top: auto;
  padding-top: var(--space-4);
  border-top: 1px solid var(--border-subtle);
}

/* Mobile: hide by default; the TopBar opens a slide-in drawer. */
@media (max-width: 899px) {
  .sidebar {
    position: fixed;
    inset: 0 auto 0 0;
    transform: translateX(-100%);
    transition: transform var(--transition-base);
    z-index: 50;
    box-shadow: var(--shadow-lg);
  }
  .sidebarOpen {
    transform: translateX(0);
  }
  .scrim {
    position: fixed;
    inset: 0;
    background: var(--bg-overlay);
    border: none;
    padding: 0;
    margin: 0;
    z-index: 40;
  }
}
```

- [ ] **Step 12.2: Create `Sidebar.tsx`**

```tsx
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Logo } from "@/components/ui/Logo";
import { cn } from "@/lib/utils/cn";
import { useAuth } from "@/lib/hooks/useAuth";
import type { ReactNode } from "react";
import styles from "./Sidebar.module.css";

interface NavItem {
  href: string;
  label: string;
}

const PRIMARY_ITEMS: NavItem[] = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/documents", label: "Documents" },
  { href: "/chat", label: "Chat" },
];

interface Props {
  open: boolean;
  onClose(): void;
}

export function Sidebar({ open, onClose }: Props): ReactNode {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <>
      {open ? (
        <button
          aria-label="Close navigation"
          className={styles.scrim}
          onClick={onClose}
        />
      ) : null}
      <aside
        className={cn(styles.sidebar, open && styles.sidebarOpen)}
        aria-label="Primary navigation"
      >
        <div className={styles.brand}>
          <Link href="/" onClick={onClose}>
            <Logo />
          </Link>
        </div>

        <nav className={styles.nav} aria-label="Main">
          <div className={styles.section}>Workspace</div>
          {PRIMARY_ITEMS.map((item) => {
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(styles.link, active && styles.linkActive)}
                aria-current={active ? "page" : undefined}
                onClick={onClose}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className={styles.footer}>
          {user ? (
            <>
              <div style={{ fontSize: "var(--text-sm)", color: "var(--fg-secondary)" }}>
                {user.email}
              </div>
              <button
                type="button"
                onClick={logout}
                className={styles.link}
                style={{ background: "transparent", border: "none", cursor: "pointer", width: "100%", textAlign: "left", marginTop: "var(--space-2)" }}
              >
                Sign out
              </button>
            </>
          ) : (
            <Link href="/login" className={styles.link} onClick={onClose}>
              Sign in
            </Link>
          )}
        </div>
      </aside>
    </>
  );
}
```

- [ ] **Step 12.3: Create `TopBar.module.css`**

```css
.bar {
  display: none;
  align-items: center;
  gap: var(--space-3);
  height: 56px;
  padding: 0 var(--space-4);
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-subtle);
  position: sticky;
  top: 0;
  z-index: 30;
}

.menuButton {
  background: transparent;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  color: var(--fg-primary);
  width: 36px;
  height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.title {
  font-weight: 600;
  font-size: var(--text-base);
  color: var(--fg-primary);
}

@media (max-width: 899px) {
  .bar {
    display: flex;
  }
}
```

- [ ] **Step 12.4: Create `TopBar.tsx`**

```tsx
"use client";

import { Logo } from "@/components/ui/Logo";
import styles from "./TopBar.module.css";

interface Props {
  onToggleSidebar(): void;
}

export function TopBar({ onToggleSidebar }: Props) {
  return (
    <header className={styles.bar} role="banner">
      <button
        type="button"
        aria-label="Open navigation"
        className={styles.menuButton}
        onClick={onToggleSidebar}
      >
        {/* 16x16 hamburger — pure CSS, no asset. */}
        <svg
          width="16"
          height="16"
          viewBox="0 0 16 16"
          aria-hidden="true"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
        >
          <path d="M2 4h12M2 8h12M2 12h12" />
        </svg>
      </button>
      <div className={styles.title}>
        <Logo size="sm" />
      </div>
    </header>
  );
}
```

- [ ] **Step 12.5: Create `PageContainer.module.css`**

```css
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--space-8) var(--space-6);
  width: 100%;
}

@media (max-width: 600px) {
  .container {
    padding: var(--space-6) var(--space-4);
  }
}
```

- [ ] **Step 12.6: Create `PageContainer.tsx`**

```tsx
import type { ReactNode } from "react";
import styles from "./PageContainer.module.css";

interface Props {
  children: ReactNode;
}

export function PageContainer({ children }: Props) {
  return <div className={styles.container}>{children}</div>;
}
```

- [ ] **Step 12.7: Create `AppShell.module.css`**

```css
.shell {
  display: flex;
  align-items: stretch;
  min-height: 100vh;
  background: var(--bg-canvas);
}

.main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.mobileOnlyTopBar {
  display: block;
}

@media (min-width: 900px) {
  .mobileOnlyTopBar {
    display: none;
  }
}
```

- [ ] **Step 12.8: Create `AppShell.tsx`**

```tsx
"use client";

import { useEffect, useState, type ReactNode } from "react";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import styles from "./AppShell.module.css";

interface Props {
  children: ReactNode;
}

export function AppShell({ children }: Props) {
  const [open, setOpen] = useState(false);

  // Close the mobile drawer on route change (resize to desktop too).
  useEffect(() => {
    const mq = window.matchMedia("(min-width: 900px)");
    const onChange = (e: MediaQueryListEvent) => {
      if (e.matches) setOpen(false);
    };
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  // ESC closes the drawer.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <div className={styles.shell}>
      <Sidebar open={open} onClose={() => setOpen(false)} />
      <div className={styles.main}>
        <div className={styles.mobileOnlyTopBar}>
          <TopBar onToggleSidebar={() => setOpen((o) => !o)} />
        </div>
        <main role="main">{children}</main>
      </div>
    </div>
  );
}
```

- [ ] **Step 12.9: Commit**

```bash
git add frontend/src/components/layout
git commit -m "feat(shell): AppShell + Sidebar + TopBar + PageContainer (responsive, no fake data)"
```

---

## Task 13: Marketing/landing page (no fake content)

**Files:**
- Modify: `frontend/src/app/page.tsx`

This is the root route. It does NOT yet need to do anything product-y. We render a calm landing that demonstrates the shell: shows the brand mark, a one-line tagline, and two actions (`Sign in`, `Create account`). The body lives inside `AppShell` so future authenticated pages can reuse it.

- [ ] **Step 13.1: Replace `src/app/page.tsx`**

```tsx
import Link from "next/link";
import { AppShell } from "@/components/layout/AppShell";
import { PageContainer } from "@/components/layout/PageContainer";
import { Button } from "@/components/ui/Button";
import { Logo } from "@/components/ui/Logo";
import styles from "./page.module.css";

export default function HomePage() {
  return (
    <AppShell>
      <PageContainer>
        <section className={styles.hero}>
          <Logo size="md" />
          <h1 className={styles.title}>
            Your AI-powered academic operating system.
          </h1>
          <p className={styles.lede}>
            Upload papers, ask grounded questions, and study with citations —
            all from one calm workspace.
          </p>
          <div className={styles.actions}>
            <Link href="/register">
              <Button variant="primary">Create account</Button>
            </Link>
            <Link href="/login">
              <Button variant="secondary">Sign in</Button>
            </Link>
          </div>
        </section>
      </PageContainer>
    </AppShell>
  );
}
```

- [ ] **Step 13.2: Replace `src/app/page.module.css`**

```css
.hero {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  align-items: flex-start;
  padding: var(--space-12) 0;
}

.title {
  font-size: var(--text-3xl);
  line-height: var(--leading-tight);
  font-weight: 600;
  letter-spacing: -0.02em;
  margin: 0;
  max-width: 22ch;
  color: var(--fg-primary);
}

.lede {
  font-size: var(--text-lg);
  line-height: var(--leading-normal);
  color: var(--fg-secondary);
  margin: 0;
  max-width: 52ch;
}

.actions {
  display: flex;
  gap: var(--space-3);
  flex-wrap: wrap;
  margin-top: var(--space-2);
}

@media (max-width: 600px) {
  .hero {
    padding: var(--space-6) 0;
  }
  .title {
    font-size: var(--text-2xl);
  }
  .lede {
    font-size: var(--text-base);
  }
}
```

- [ ] **Step 13.3: Commit**

```bash
git add frontend/src/app/page.tsx frontend/src/app/page.module.css
git commit -m "feat(landing): calm hero on the shared AppShell"
```

---

## Task 14: Route groups — (auth) and (app) — skeleton pages

**Files:**
- Create: `frontend/src/app/(auth)/layout.tsx`
- Create: `frontend/src/app/(auth)/login/page.tsx`
- Create: `frontend/src/app/(auth)/register/page.tsx`
- Create: `frontend/src/app/(app)/layout.tsx`
- Create: `frontend/src/app/(app)/dashboard/page.tsx`
- Create: `frontend/src/app/(app)/documents/page.tsx`
- Create: `frontend/src/app/(app)/chat/page.tsx`

Note: Each page is intentionally minimal. Phase 4A establishes the route surface; Phase 4B+ will fill in real forms, document list, chat composer, etc. Skeleton pages MUST use the `LoadingState` / `EmptyState` primitives to demonstrate they will eventually be API-driven.

- [ ] **Step 14.1: Create `src/app/(auth)/layout.tsx`**

```tsx
import type { ReactNode } from "react";
import styles from "./layout.module.css";
import { Logo } from "@/components/ui/Logo";

interface Props {
  children: ReactNode;
}

export default function AuthLayout({ children }: Props) {
  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <Logo size="sm" />
      </header>
      <main className={styles.main}>{children}</main>
    </div>
  );
}
```

```css
/* (auth)/layout.module.css */
.shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--bg-canvas);
}

.header {
  padding: var(--space-4) var(--space-6);
  border-bottom: 1px solid var(--border-subtle);
  background: var(--bg-surface);
}

.main {
  flex: 1;
  display: grid;
  place-items: center;
  padding: var(--space-8) var(--space-4);
}
```

- [ ] **Step 14.2: Create `src/app/(auth)/login/page.tsx`**

```tsx
import { LoginForm } from "./LoginForm";

export default function LoginPage() {
  return <LoginForm />;
}
```

- [ ] **Step 14.3: Create `src/app/(auth)/login/LoginForm.tsx`**

```tsx
"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/hooks/useAuth";
import { Button } from "@/components/ui/Button";
import { ErrorState } from "@/components/primitives/ErrorState";
import styles from "./form.module.css";

export function LoginForm() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setPending(true);
    setError(null);
    try {
      await login({ email, password });
      router.replace("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-in failed");
    } finally {
      setPending(false);
    }
  }

  return (
    <form className={styles.card} onSubmit={onSubmit} noValidate>
      <h1 className={styles.title}>Sign in</h1>
      <p className={styles.lede}>Use your AcademicOS account.</p>

      <label className={styles.field}>
        <span className={styles.label}>Email</span>
        <input
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className={styles.input}
        />
      </label>

      <label className={styles.field}>
        <span className={styles.label}>Password</span>
        <input
          type="password"
          autoComplete="current-password"
          required
          minLength={8}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className={styles.input}
        />
      </label>

      {error ? <ErrorState title="Could not sign you in" description={error} /> : null}

      <Button type="submit" variant="primary" fullWidth disabled={pending}>
        {pending ? "Signing in…" : "Sign in"}
      </Button>

      <div className={styles.foot}>
        New here? <Link href="/register">Create an account</Link>
      </div>
    </form>
  );
}
```

- [ ] **Step 14.4: Create `src/app/(auth)/login/form.module.css`**

```css
.card {
  width: 100%;
  max-width: 380px;
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: var(--space-8);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  box-shadow: var(--shadow-sm);
}

.title {
  margin: 0;
  font-size: var(--text-2xl);
  font-weight: 600;
  color: var(--fg-primary);
}

.lede {
  margin: 0;
  color: var(--fg-secondary);
  font-size: var(--text-sm);
}

.field {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.label {
  font-size: var(--text-sm);
  color: var(--fg-secondary);
  font-weight: 500;
}

.input {
  background: var(--bg-canvas);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-md);
  padding: var(--space-3) var(--space-4);
  color: var(--fg-primary);
  font-size: var(--text-base);
  transition: border-color var(--transition-fast);
}
.input:focus {
  border-color: var(--accent);
  outline: none;
}

.foot {
  margin-top: var(--space-2);
  font-size: var(--text-sm);
  color: var(--fg-secondary);
  text-align: center;
}
```

> The `(auth)/register` folder will reuse these styles. Easiest: copy `form.module.css` next to it. (CSS-modules are scoped per file.)

- [ ] **Step 14.5: Create `src/app/(auth)/register/page.tsx`**

```tsx
import { RegisterForm } from "./RegisterForm";

export default function RegisterPage() {
  return <RegisterForm />;
}
```

- [ ] **Step 14.6: Create `src/app/(auth)/register/RegisterForm.tsx`**

```tsx
"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/hooks/useAuth";
import { Button } from "@/components/ui/Button";
import { ErrorState } from "@/components/primitives/ErrorState";
import styles from "../login/form.module.css";

export function RegisterForm() {
  const { register } = useAuth();
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setPending(true);
    setError(null);
    try {
      await register({ full_name: fullName, email, password });
      router.replace("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create account");
    } finally {
      setPending(false);
    }
  }

  return (
    <form className={styles.card} onSubmit={onSubmit} noValidate>
      <h1 className={styles.title}>Create your account</h1>
      <p className={styles.lede}>It takes about thirty seconds.</p>

      <label className={styles.field}>
        <span className={styles.label}>Full name</span>
        <input
          required
          minLength={1}
          maxLength={255}
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          className={styles.input}
        />
      </label>

      <label className={styles.field}>
        <span className={styles.label}>Email</span>
        <input
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className={styles.input}
        />
      </label>

      <label className={styles.field}>
        <span className={styles.label}>Password</span>
        <input
          type="password"
          autoComplete="new-password"
          required
          minLength={8}
          maxLength={128}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className={styles.input}
        />
      </label>

      {error ? (
        <ErrorState title="Could not create your account" description={error} />
      ) : null}

      <Button type="submit" variant="primary" fullWidth disabled={pending}>
        {pending ? "Creating…" : "Create account"}
      </Button>

      <div className={styles.foot}>
        Already have an account? <Link href="/login">Sign in</Link>
      </div>
    </form>
  );
}
```

- [ ] **Step 14.7: Create `src/app/(app)/layout.tsx`**

```tsx
"use client";

import { useEffect, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/layout/AppShell";
import { LoadingState } from "@/components/primitives/LoadingState";
import { useAuth } from "@/lib/hooks/useAuth";

export default function AppLayout({ children }: { children: ReactNode }) {
  const { status } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (status === "unauthenticated") router.replace("/login");
  }, [status, router]);

  if (status !== "authenticated") return <LoadingState label="Checking your session…" />;
  return <AppShell>{children}</AppShell>;
}
```

- [ ] **Step 14.8: Create `src/app/(app)/dashboard/page.tsx`**

```tsx
import { PageContainer } from "@/components/layout/PageContainer";
import { EmptyState } from "@/components/primitives/EmptyState";

export default function DashboardPage() {
  return (
    <PageContainer>
      <EmptyState
        title="Dashboard is coming in a later phase"
        description="Today it just exists to prove routing and the application shell work end-to-end."
      />
    </PageContainer>
  );
}
```

- [ ] **Step 14.9: Create `src/app/(app)/documents/page.tsx`**

```tsx
import { PageContainer } from "@/components/layout/PageContainer";
import { EmptyState } from "@/components/primitives/EmptyState";

export default function DocumentsPage() {
  return (
    <PageContainer>
      <EmptyState
        title="No documents yet"
        description="The document manager will land in Phase 4B."
      />
    </PageContainer>
  );
}
```

- [ ] **Step 14.10: Create `src/app/(app)/chat/page.tsx`**

```tsx
import { PageContainer } from "@/components/layout/PageContainer";
import { EmptyState } from "@/components/primitives/EmptyState";

export default function ChatPage() {
  return (
    <PageContainer>
      <EmptyState
        title="Chat is coming soon"
        description="The grounded chat UI will land in a later phase."
      />
    </PageContainer>
  );
}
```

- [ ] **Step 14.11: Commit**

```bash
git add frontend/src/app
git commit -m "feat(routes): (auth) + (app) route groups with skeleton pages"
```

---

## Task 15: Wire providers into the root layout

**Files:**
- Modify: `frontend/src/app/layout.tsx`

Add the `AuthProvider` so every client component has access to `useAuth`. Do NOT add other providers — none are justified yet.

- [ ] **Step 15.1: Replace `src/app/layout.tsx`**

```tsx
import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { ReticleDev } from "./reticle-dev";
import { AuthProvider } from "@/lib/context/AuthContext";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "AcademicOS",
  description: "Your AI-powered academic operating system.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable}`}>
      <body>
        <AuthProvider>{children}</AuthProvider>
        {process.env.NODE_ENV === "development" ? <ReticleDev /> : null}
      </body>
    </html>
  );
}
```

- [ ] **Step 15.2: Commit**

```bash
git add frontend/src/app/layout.tsx
git commit -m "feat(layout): mount AuthProvider alongside ReticleDev"
```

---

## Task 16: ESLint + typecheck scripts in `package.json`

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/eslint.config.mjs`

The default scaffold has no `lint` script. We add `next lint` (flat) plus a `typecheck` script that does `tsc --noEmit`. Spec Step 16 requires `npm run lint` and `npx tsc --noEmit` to pass before completion.

- [ ] **Step 16.1: Add ESLint flat config**

Create `frontend/eslint.config.mjs` (Next 16 supports flat config; `next lint` uses it):

```js
import { FlatCompat } from "@eslint/eslintrc";
import { dirname } from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const compat = new FlatCompat({ baseDirectory: __dirname });

const config = [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    ignores: [".next/**", "node_modules/**", "next-env.d.ts"],
  },
];

export default config;
```

- [ ] **Step 16.2: Add ESLint deps**

Run: `cd frontend && npm install --save-dev eslint @eslint/eslintrc eslint-config-next 2>&1 | tail -10`
Expected: installs cleanly. (Next publishes `eslint-config-next`; the flat-config shim uses `@eslint/eslintrc`.)

- [ ] **Step 16.3: Update `package.json` scripts**

Edit `frontend/package.json` — replace `"scripts":` with:

```json
"scripts": {
  "dev": "next dev",
  "build": "next build",
  "start": "next start",
  "lint": "next lint",
  "typecheck": "tsc --noEmit"
}
```

- [ ] **Step 16.4: Run `npm run lint`**

Run: `cd frontend && npm run lint 2>&1 | tail -30`
Expected: zero errors. If any appear, fix the file referenced (do NOT add inline disables unless truly necessary).

- [ ] **Step 16.5: Run `npm run typecheck`**

Run: `cd frontend && npm run typecheck 2>&1 | tail -20`
Expected: zero errors.

- [ ] **Step 16.6: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/eslint.config.mjs
git commit -m "chore(frontend): enable ESLint flat config + typecheck script"
```

---

## Task 17: End-to-end validation

**Files:** none — runtime verification only.

Run every spec-mandated check. Record exact output in the final report.

- [ ] **Step 17.1: Lint**

Run: `cd frontend && npm run lint 2>&1 | tail -10`
Expected: `✔ No ESLint warnings or errors`.

- [ ] **Step 17.2: Typecheck**

Run: `cd frontend && npm run typecheck 2>&1 | tail -10`
Expected: zero output.

- [ ] **Step 17.3: Production build**

Run: `cd frontend && npm run build 2>&1 | tail -30`
Expected: clean `Compiled successfully` line; route summary listing `/`, `/login`, `/register`, `/dashboard`, `/documents`, `/chat`.

- [ ] **Step 17.4: Dev server smoke test**

Run (with timeout): `cd frontend && timeout 20 npm run dev 2>&1 | head -40`
Expected: server starts, prints the local URL, no compile errors. The timeout kills the server after 20s — that's fine for this gate.

Manually: confirm `ReticleDev` is mounted in dev (`localhost:3000` → DevTools → no Reticle SDK bytes in static bundle). Confirm `npm run build` output excludes the Reticle polyfill import — verify the `ReticleDev` `import('@reticlehq/react')` is reachable only in dev (it's behind a `process.env.NODE_ENV === "development"` guard at the React-tree level; the dynamic import lives inside `ReticleDev` which is conditionally rendered).

- [ ] **Step 17.5: Backend regression**

Run: `cd backend && pytest -q 2>&1 | tail -10`
Expected: `164 passed`. If more tests run (e.g. fixtures strengthened), report the new total — but it MUST be `0 failed`.

- [ ] **Step 17.6: Final commit if anything straggled**

```bash
git status
# If clean → no commit. If anything residual:
git add -A && git commit -m "chore(frontend): Phase 4A leftover tidy-up"
```

- [ ] **Step 17.7: Produce the final report**

Use the exact report template specified in the task spec.

---

## Out of scope (Phase 4B+)

Per Step 15 of the spec, the following are NOT built here and remain for later phases:
- Real dashboard data, document upload UI, document library, PDF viewer, AI chat composer, conversation sidebar, streaming responses, citation UI, study planner, flashcards, quizzes, exam prep, memory system, LangGraph integration, multi-agent UI, notifications, analytics.

---

## Self-Review

**1. Spec coverage:**
- Architecture (§2) → Tasks 1–6, 12, 14
- Design system / tokens (§3, §4) → Tasks 9, 10
- Global layout (§5) → Task 9, 15
- API client (§6) → Tasks 4, 6
- Env vars (§7) → Task 1
- Types (§8) → Task 2
- Auth (§9) → Tasks 5, 7, 8
- App shell (§10) → Task 12
- Responsiveness (§11) → Task 12 (CSS media queries + TopBar drawer)
- Accessibility (§12) → Tasks 10, 11, 12 (`aria-label`, `aria-current`, `role="alert"`, `aria-live`, semantic `<aside>/<main>/<header>/<nav>`, focus-visible rule, ESC key handler)
- Reticle preservation (§13) → no changes to `reticle-dev.tsx` or `next.config.ts`; explicit mention in Tasks 15 and 17
- Error/Loading foundations (§14) → Task 11
- Explicit "do not build" (§15) → not touched anywhere
- Lint/typecheck/build (§16) → Tasks 16, 17
- Backend regression (§17) → Task 17.5

**2. Placeholder scan:** None — every step has the exact code or command.

**3. Type consistency:** `TokenResponse`, `User`, `Document`, `DocumentUploadStatus`, `ChatSession`, `ChatMessage`, `ChatMessageWithSources`, `ChatMessageSource`, `ChatSessionWithMessages`, `ChatRequest`, `ChatResponse`, `ChatSource`, `SendMessagePayload`, `SendMessageResponse`, `CreateSessionPayload`, `UpdateSessionPayload`, `SearchRequest`, `SearchResponse`, `RetrievedChunk`, `APIError`, `UUID`, `LoginPayload`, `RegisterPayload` all match the backend Pydantic contracts verified during the audit. `apiFetch` signature matches the call sites in Task 6. The auth context exposes exactly the fields used by Sidebar and the forms.

**Identified gaps fixed in this plan:**
- The original draft of Task 6 declared `Void` inside `chat.ts`; corrected to use a `Void` type exported from `@/types/api` and import it normally.
- `@/lib/auth/guards.ts` is JSX, not plain TS — renamed to `.tsx` so the JSX compiles without configuration changes.
