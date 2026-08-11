# AcademicOS — Project Memory

> **Purpose:** the next coding session reads this file first. It contains
> the architecture, the completed phases, the contracts, the file paths,
> and the next planned phase. Do not rewrite Phase 4A or 4B code on the
> basis of stale assumptions — this memory is the continuity source.

---

## Current project architecture

AcademicOS is a two-tier monorepo:

```
D:/AI ML/projects/AcademicOS/
├── backend/     FastAPI 0.115 + SQLAlchemy 2 (async) + Pydantic v2 + Alembic
├── frontend/    Next.js 16.3 (App Router, Turbopack) + React 19.2 + TS 5 (strict)
├── docs/        Phase implementation plans (superpowers plans live under docs/superpowers/plans/)
└── memory.md    THIS FILE
```

**Backend stack**

- Python 3.11+, FastAPI under `/api/v1`, async SQLAlchemy w/ Postgres, Alembic migrations.
- Auth: stateless JWT bearer tokens (HS256, `SECRET_KEY` from settings). No refresh tokens yet.
- LLM: Gemini (`google.generativeai`) — behind `app.llm.provider.get_llm_provider`.
- Vector store: Qdrant, embedding provider: SentenceTransformer (local).
- Tests: pytest, **164 passed / 0 failed** (Phase 4B baseline preserved).

**Frontend stack**

- Next.js 16 App Router. Route groups: `(auth)` for login/register (public), `(app)` for dashboard/documents/chat (protected).
- Styling: CSS Modules + CSS custom-property design tokens in `src/app/globals.css`. **No Tailwind. No UI library.** Dark-first theme.
- API: central typed `apiFetch<T>()` in `src/lib/api/client.ts` with bearer-token awareness and `APIError` normalization. Domain modules: `auth.ts`, `documents.ts`, `chat.ts`, `search.ts`.
- Auth: `localStorage` (key `academicos:auth:token`) + React Context (`AuthContext` + `useAuth`). Bootstrap validates stored tokens against `/auth/me`.
- Routing protection: `(app)/layout.tsx` redirects unauthenticated users to `/login`.
- Reticle: `@reticlehq/next` (prod no-op) + `ReticleDev` (dev-only render). Do NOT reconfigure.
- Test runner: **Vitest + React Testing Library** (added in Phase 4B).

---

## Completed phases

| Phase | Scope | Status |
|---|---|---|
| 1 | Backend foundation (config, db, models, schemas, deps) | ✅ Complete |
| 2 | Document processing + embeddings + RAG retrieval | ✅ Complete |
| 3 | Chat sessions, messages, sources | ✅ Complete + stabilized |
| 4A | Frontend foundation (design system, shell, auth wiring, API client, routes) | ✅ Complete |
| **4B** | **Authentication UI + backend integration** | **✅ Complete** |

---

## Phase 4A — Frontend Foundation (summary)

Implementation plan: `docs/superpowers/plans/2026-08-10-phase-4a-frontend-foundation.md`.

Established:

- App Router structure (`src/app/(auth)`, `src/app/(app)`, root `src/app/page.tsx`).
- Design tokens (`src/app/globals.css`): dark-first, all colors/spacing/radii as CSS variables.
- Reusable UI primitives: `Button`, `Logo`, `LoadingState`, `ErrorState`, `EmptyState`.
- Layout shell: `AppShell` + `Sidebar` (responsive, drawer on `<900px`) + `TopBar` + `PageContainer`.
- Typed `apiFetch` + domain modules.
- `AuthContext` skeleton + `useAuth` hook + `RequireAuth`/`RedirectIfAuthed` guards.
- ESLint flat config (`eslint-config-next/core-web-vitals` + `/typescript`).
- Reticle wiring preserved.

---

## Phase 4B — Authentication UI + Backend Integration (summary)

> **Important:** Phase 4B did NOT rewrite Phase 4A auth code. Inspection
> of the on-disk source confirmed Phase 4A already shipped full Login +
> Register forms, the `AuthContext` with bootstrap, the typed `apiFetch`,
> the `(app)/layout.tsx` route guard, and the public `(auth)` route
> group. Phase 4B therefore focused on **(a)** writing tests that prove
> the existing behavior and **(b)** documenting the architecture.
> See the "Known issue" section below for an important caveat about
> the Phase 4A commit.

### Backend contracts verified

Inspected live code under `backend/app/api/v1/endpoints/auth.py` + `app/schemas/auth.py` + `app/schemas/user.py` + `app/api/deps.py`.

| Endpoint | Method | Path | Auth | Request | Response | Notable errors |
|---|---|---|---|---|---|---|
| Register | POST | `/api/v1/auth/register` | none | `{full_name: str (1-255), email: EmailStr, password: str (8-128)}` | `201` + `UserResponse` (`id`, `full_name`, `email`, `is_active`, `is_verified`, `created_at`, `updated_at`) | `400 "Email already registered"`, `422` validation array |
| Login | POST | `/api/v1/auth/login` | none | `{email: EmailStr, password: str (8-128)}` | `200` + `{access_token: str, token_type: "bearer"}` | `401 "Incorrect email or password"`, `403 "Inactive account"` |
| Current user | GET | `/api/v1/auth/me` | bearer | none | `200` + `UserResponse` | `401 "Not authenticated" / "Token has expired" / "Could not validate credentials"`, `403 "Inactive account"` |

Authentication header: `Authorization: Bearer <access_token>`. The backend (`OAuth2PasswordBearer` in `app/api/deps.py`) does NOT auto-reject on missing token — it returns 401 with `WWW-Authenticate: Bearer`.

**Critical behavioral fact:** `/auth/register` does NOT return a token. The frontend's `AuthContext.register()` calls `/auth/register` and then `/auth/login` automatically. (Phase 4B explicitly chose this over inventing a separate "verify email" flow that the backend doesn't implement.)

### Frontend architecture (auth-specific)

- **Auth state**: `src/lib/context/AuthContext.tsx` exposes `{ status, user, accessToken, login, register, logout, refreshUser }`. `status: "loading" | "authenticated" | "unauthenticated"`.
- **API client**: `src/lib/api/client.ts` (`apiFetch<T>()`). Attaches `Authorization: Bearer …` from `localStorage` whenever `auth !== false`. Throws `APIError(message, status, payload)` on non-2xx; normalizes FastAPI's `{detail: string | array}`.
- **Token storage**: `src/lib/auth/storage.ts`. Keys: `academicos:auth:token`, `academicos:auth:user`. SSR-safe (`typeof window` guards). Helpers: `getStoredToken`, `setStoredToken`, `clearStoredAuth`, `getStoredUserJSON<T>()`, `setStoredUserJSON<T>(user)`.
- **Bootstrap**: `AuthProvider` `useEffect` reads the stored token, calls `/auth/me`. On success → `authenticated` + cached user. On failure → `clearStoredAuth()` + `unauthenticated`.
- **Route protection**: `src/app/(app)/layout.tsx` redirects unauthenticated users to `/login` and renders `<LoadingState>` while `status === "loading"`. No protected-content flicker. `/login` and `/register` live under `(auth)/` and are publicly accessible (per spec §9).
- **Forms**: `src/app/(auth)/login/LoginForm.tsx` and `…/register/RegisterForm.tsx`. Client-side validation matches backend constraints (password 8-128 chars, full_name 1-255 chars). Backend errors are rendered via `ErrorState`. Submit button is disabled and shows a pending label while the request is in flight. On success: `router.replace("/dashboard")`.

### Security posture

- No JWT logging, no password logging, no token rendering in UI.
- No secrets in `frontend/.env*`. All public env vars are prefixed `NEXT_PUBLIC_`. Backend `SECRET_KEY`, `GEMINI_API_KEY`, DB URL, etc. never reach the browser.
- Frontend route protection is UX-only; the backend remains the authorization authority (`get_current_active_user` in `app/api/deps.py`).
- No fake auth, no mock login, no client-only JWT validation.

### Files created in Phase 4B

- `frontend/vitest.config.ts` — Vitest config (jsdom + `@/*` alias).
- `frontend/vitest.setup.ts` — registers `@testing-library/jest-dom` matchers + RTL `cleanup`.
- `frontend/src/test-utils/renderAuth.tsx` — `<AuthProvider>` probe for AuthContext tests.
- `frontend/src/test-utils/wrappers.tsx` — `renderWithAuth()` for forms that consume `useAuth` from a stubbed context.
- `frontend/src/lib/api/__tests__/client.test.ts` — `apiFetch`: bearer header, error normalization, 204 handling.
- `frontend/src/lib/api/__tests__/auth.test.ts` — `authApi` contract for `/register`, `/login`, `/me`.
- `frontend/src/lib/context/__tests__/AuthContext.test.tsx` — bootstrap (no token / valid token / expired token), login (success + 401), register (auto-login + 400 duplicate), logout, refresh.
- `frontend/src/app/(auth)/login/__tests__/LoginForm.test.tsx` — happy path + 401 error + pending state + /register link.
- `frontend/src/app/(auth)/register/__tests__/RegisterForm.test.tsx` — happy path + 400 duplicate + pending state + /login link.
- `frontend/memory.md` — this file.

### Files modified in Phase 4B

- `frontend/package.json` — added `vitest`, `@vitest/coverage-v8`, `@testing-library/react`, `@testing-library/jest-dom`, `@testing-library/user-event`, `jsdom`. Added `test` and `test:watch` scripts.
- `frontend/eslint.config.mjs` — added ignores for `vitest.config.ts`, `vitest.setup.ts`, and `src/**/*.test.{ts,tsx}`.

---

## Important frontend decisions (Phase 4B)

1. **JWT in localStorage, not a cookie.** Rationale (recorded in `src/lib/auth/storage.ts`): backend is stateless bearer-only, cookies imply CSRF and a server in the loop, localStorage keeps the shell deployable as a static export.
2. **`register()` auto-logs-in by calling `/auth/login` afterwards.** The backend does NOT issue a token on register. Do NOT introduce a separate "verify email" or "wait for confirmation" step — that doesn't exist.
3. **Bootstrap MUST call `/auth/me`, not just trust the stored token.** Otherwise an expired token would leave the app in an inconsistent state until the next protected request.
4. **`(app)/layout.tsx` IS the route guard.** `RequireAuth`/`RedirectIfAuthed` in `src/lib/auth/guards.tsx` exist but the protected pages are guarded at the layout level instead (simpler, no per-page wrapper).
5. **Forms live alongside their page in the route group**, not in `src/components/`. They are page-internal.

---

## API contracts used (auth surface)

See the table above. Full surface for all endpoints lives in `frontend/src/lib/constants/api.ts` (`API_PATHS`).

---

## Known constraints

- **Reticle**: `ReticleDev` is gated by `process.env.NODE_ENV === "development"` in `src/app/layout.tsx`. Do not move it. `withReticle` in `next.config.ts` is a prod no-op and stays.
- **No Tailwind. No UI library.** All styles are CSS Modules + design tokens.
- **`localStorage` only.** No cookies for auth. No SSR-side auth middleware.
- **Next.js 16.3.0 has breaking changes vs. older training data.** Read `node_modules/next/dist/docs/` before writing `src/app/` code. Heed deprecation notices.
- **Backend tests must remain 164 passed / 0 failed.** Frontend changes do not modify backend tests.
- **`ESM` warning from Vitest config (`.ts` file).** Harmless future-deprecation notice from Vite 7; ignored.

---

## ⚠️ Known issue uncovered during Phase 4B

The Phase 4A commit (`7ee68cb`) appeared to ship everything under `frontend/src/lib/` — auth context, API client, storage helpers, hooks, utils — but in fact those files were **silently filtered by the root `.gitignore`**. Line 19 read `lib/` (Python venv pattern), which matched `frontend/src/lib/` too. The fix (committed alongside Phase 4B) is `/lib/` and `/lib64/` (root-anchored). Net effect:

- Before the fix: `git status` showed `frontend/src/lib/` as untracked even after Phase 4A was "done".
- After the fix: the files are now in the repo. Treat the Phase 4B commit as the *de facto* point at which the full Phase 4A source first became part of version control.

**Lesson for future phases:** always run `git status` *after* `git commit` and verify that what you intended to land actually landed. The "Phase 4A complete" message in the commit body did not match the on-disk reality.

---

## Test commands

From `frontend/`:

```bash
npm run lint           # ESLint flat config — must be clean
npm run typecheck      # tsc --noEmit — must be clean
npm test               # Vitest one-shot — currently 28 passed
npm run test:watch     # Vitest watch mode
npm run build          # Next.js production build — must compile successfully
```

From `backend/`:

```bash
pytest -q              # MUST end with 164 passed, 0 failed
```

---

## Current test results (after Phase 4B)

| Check | Result |
|---|---|
| `npm run lint` | PASS — 0 errors, 0 warnings |
| `npm run typecheck` | PASS — 0 errors |
| `npm test` | PASS — **28 passed / 0 failed** across 5 test files |
| `npm run build` | PASS — 7 routes (`/`, `/login`, `/register`, `/dashboard`, `/documents`, `/chat`, `/_not-found`) |
| `pytest -q` | PASS — **164 passed / 0 failed** |

---

## Exact next planned phase

### Phase 4C — Dashboard + Core AcademicOS Application Shell

Goals (NOT yet implemented):

- Real dashboard data (recent documents, recent chats, study progress).
- Document upload UI + document library + PDF viewer.
- Grounded chat composer + conversation sidebar + streaming responses + citation UI.
- App-wide notifications.

Do NOT start Phase 4C until explicitly authorized. Read this memory first, then read the git log of recent commits, then plan.

---

## Backend contracts reference (full surface)

Quick reference; full files in `backend/app/api/v1/endpoints/*.py` and `backend/app/schemas/*.py`.

- `POST /api/v1/auth/register` — see Phase 4B table.
- `POST /api/v1/auth/login` — see Phase 4B table.
- `GET  /api/v1/auth/me` — see Phase 4B table.
- `POST /api/v1/documents/upload` — multipart, field `file`.
- `GET  /api/v1/documents?skip=&limit=` — list.
- `GET  /api/v1/documents/{id}` — detail.
- `DELETE /api/v1/documents/{id}`.
- `POST /api/v1/search` — `{query, top_k?, score_threshold?, document_id?, mode?}`.
- `POST /api/v1/chat` — one-shot, no session persistence.
- `POST /api/v1/chat/sessions`, `GET /api/v1/chat/sessions`, `GET /api/v1/chat/sessions/{id}`, `PATCH …`, `DELETE …`, `POST /api/v1/chat/sessions/{id}/messages`.

---

## How the next session should start

1. Read this `memory.md`.
2. `git log --oneline -10` to see what's been done since.
3. `git status` to see if anything's in progress.
4. Plan, then implement. **Do not** reimplement Phase 4A or 4B unless the task explicitly says so.
