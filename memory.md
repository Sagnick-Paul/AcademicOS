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
| 4B | Authentication UI + backend integration | ✅ Complete |
| **4C** | **Dashboard + Core Application Shell** | **✅ Complete** |

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
| `npm test` | PASS — **47 passed / 0 failed** across 9 test files |
| `npm run build` | PASS — 7 routes (`/`, `/login`, `/register`, `/dashboard`, `/documents`, `/chat`, `/_not-found`) |
| `pytest -q` | PASS — **164 passed / 0 failed** |

---

## Exact next planned phase

### Phase 4D — Document management + Library UI (NOT yet implemented)

Goals:

- Document upload UI (drag-and-drop + click-to-browse) using `documentsApi.upload()`.
- Library list view that shows each document's filename, upload status, file type, size.
- Simple document detail view.
- Wire "recent activity" on the dashboard to show recent `Document.created_at` instead of relying on counts.
- Use real upload status + per-document error states.

Do NOT start Phase 4D until explicitly authorized. Read this memory first, then read the git log of recent commits, then plan.

---

## Phase 4C — Dashboard + Core AcademicOS Application Shell (summary)

> **Phase 4C scope note.** Phase 4C did **not** redesign Phase 4A/4B
> infrastructure. It added: (a) a real `/dashboard` with greeting,
> stats, recent activity, and quick actions; (b) a root-route
> redirector that respects auth state; (c) a polish pass on the
> Sidebar's user account area; (d) shared primary-nav config;
> (e) placeholder `/documents` and `/chat` pages that surface real
> counts; (f) tests for all of the above. No fake data anywhere.

### Purpose

Build the first real authenticated AcademicOS experience.

### Implemented

- **Application shell** — `AppShell` from Phase 4A wraps every page
  under `(app)/`. Mobile drawer, persistent desktop sidebar, ESC closes
  drawer, media-query observer resets drawer on resize.
- **Sidebar / navigation** — `Sidebar` reads `PRIMARY_NAV` from
  `src/lib/nav/config.ts` (single source of truth for nav hrefs).
  Active state uses `isNavItemActive(pathname, href)` with prefix
  matching. Each `Link` has `aria-current="page"` when active.
- **Responsive navigation** — Desktop: persistent sidebar. Mobile
  (`<900px`): sidebar slides in via `TopBar` hamburger; scrim + ESC
  close the drawer. No horizontal overflow.
- **User / account area** — `Sidebar` footer shows `user.full_name`
  (truncated with ellipsis) and `user.email`. Sign-out button calls
  `useAuth().logout()` directly. No second logout implementation.
- **Dashboard** — `/dashboard` renders:
  - A greeting derived from `Date.getHours()` + the user's first name
    (`Good morning/afternoon/evening, {firstName}`). Falls back to
    "there" when no user is present.
  - Two stat cards: **Documents** (from `documentsApi.list()`) and
    **Conversations** (from `chatApi.listSessions()`). Each shows
    `{count}` once loaded, or an inline error message if the API fails.
    Stat cards never crash the shell on failure.
  - **Recent activity** — empty state when both counts are 0; otherwise
    a "getting started" message. Never fabricates activity.
  - **Quick actions** — `Open Documents` → `/documents` and
    `Start a Chat` → `/chat` (uses `next/link`).
- **Dashboard API integration** — parallel `useEffect` fetches; each
  panel owns its own loading/error state. Failures are caught and
  surfaced, not thrown.
- **Empty states** — honest counts everywhere. New users see
  "No documents yet", "No conversations yet", "No recent activity yet".
- **Loading states** — `<LoadingState>` for dashboard initial load,
  stat panels show "Loading…".
- **Error states** — `APIError.message` is rendered in plain English
  (no stack traces, no JWTs, no backend internals).
- **Documents / Chat shell integration** — `/documents` and `/chat`
  pages now live inside `<AppShell>` via `(app)/layout.tsx` and use
  shared `PageContainer` + `EmptyState` primitives. Each surfaces
  real document/session counts from the API.
- **Root route redirect** — `src/app/page.tsx` is now a redirector.
  Authenticated → `/dashboard`. Unauthenticated → `/login`. Loading
  state renders a neutral `<LoadingState>` (no marketing hero) so the
  redirect fires cleanly on first paint.
- **Accessibility** — `aria-current="page"` on active nav, `aria-label`
  on the primary nav landmark, `aria-label` on the close-scrim button,
  `aria-label` on the menu button, semantic `<nav>`/`<aside>`/`<main>`,
  keyboard ESC closes the drawer, visible focus via the design-token
  `--focus-ring`.

### Architecture

- **Nav config (new layer)**: `src/lib/nav/config.ts` exports
  `PRIMARY_NAV` (a `readonly NavItem[]`) and `isNavItemActive()`. The
  `Sidebar` is the only consumer today; later phases (command palette,
  breadcrumbs) import from here.
- **Dashboard data flow**: `Dashboard.tsx` owns two `ResourceState<T>`
  records (one per panel). Each fetches independently, isolates
  failures, and renders a status-aware card. No global state.
- **Stat cards**: extracted into `DocumentStatCard` and
  `ConversationStatCard` with a shared `StatCard` core. The label
  drives a `data-testid` for tests.
- **Honest data**: zero manual seed data. If a backend endpoint is
  unavailable, the panel shows the error inline — the rest of the
  shell keeps working.

### Files created in Phase 4C

- `frontend/src/lib/nav/config.ts` — shared nav config + active helper.
- `frontend/src/app/(app)/dashboard/Dashboard.tsx` — client dashboard.
- `frontend/src/app/(app)/dashboard/dashboard.module.css` — dashboard styles.
- `frontend/src/app/(app)/dashboard/__tests__/Dashboard.test.tsx` — 6 tests.
- `frontend/src/app/(app)/documents/DocumentsPanel.tsx` — client panel.
- `frontend/src/app/(app)/documents/documents.module.css` — panel styles.
- `frontend/src/app/(app)/chat/ChatPanel.tsx` — client panel.
- `frontend/src/app/(app)/chat/chat.module.css` — panel styles.
- `frontend/src/app/__tests__/page.test.tsx` — root-route redirect tests.
- `frontend/src/app/(app)/__tests__/layout.test.tsx` — protected shell tests.
- `frontend/src/components/layout/__tests__/Sidebar.test.tsx` — nav tests.

### Files modified in Phase 4C

- `frontend/src/app/page.tsx` — replaced marketing landing with auth redirector.
- `frontend/src/app/page.module.css` — removed (no longer used).
- `frontend/src/app/(app)/dashboard/page.tsx` — now a thin wrapper around `<Dashboard />`.
- `frontend/src/app/(app)/documents/page.tsx` — now a thin wrapper around `<DocumentsPanel />`.
- `frontend/src/app/(app)/chat/page.tsx` — now a thin wrapper around `<ChatPanel />`.
- `frontend/src/components/layout/Sidebar.tsx` — uses shared nav config,
  user block (full_name + email + sign-out), removed inline styles.
- `frontend/src/components/layout/Sidebar.module.css` — added `.userBlock`,
  `.userName`, `.userEmail`, `.signOutButton` classes.
- `frontend/vitest.setup.ts` — added `window.matchMedia` polyfill for
  `AppShell`'s media-query observer (jsdom doesn't implement it).

### API endpoints used (Phase 4C)

- `GET /api/v1/auth/me` — already used by AuthContext bootstrap.
- `GET /api/v1/documents` — for the Documents stat card + `/documents` page count.
- `GET /api/v1/chat/sessions` — for the Conversations stat card + `/chat` page count.

No new backend endpoints were added. No backend code was modified.

### Testing summary (Phase 4C)

- **Existing tests**: 28 (Phase 4B) — all still pass.
- **New Phase 4C tests**: 19 across 4 new test files.
  - `Dashboard.test.tsx` (6): greeting with first name, fallback to "there",
    empty state (both APIs empty), real counts (non-zero), API failure
    isolation, quick-action links.
  - `Sidebar.test.tsx` (7): nav items render, active state on direct hit,
    prefix matching for nested routes, user full_name + email shown,
    logout invokes existing `logout()`, scrim only when open, nav link
    clicks invoke `onClose`.
  - `page.test.tsx` (3): loading state renders, authenticated → /dashboard,
    unauthenticated → /login.
  - `(app)/layout.test.tsx` (3): loading state, unauthenticated redirect,
    authenticated renders children.
- **Total frontend tests**: **47 passed / 0 failed** across 9 files.
- **Backend**: **164 passed / 0 failed**.
- **ESLint**: PASS.
- **TypeScript**: PASS.
- **Build**: PASS (7 routes).

### Known limitations

- The dashboard greeting uses the browser's local time only — no
  timezone-aware formatting. Acceptable for Phase 4C.
- Documents and Chat pages are still placeholders that count records
  but do not render a library or a chat composer. Those belong to
  later phases.
- The root route is a client component because it depends on
  `AuthContext`. No redirect loop; the `(app)/layout.tsx` is the
  authoritative bounce for unauthenticated users.
- `jsdom` does not implement `window.matchMedia`. Vitest setup polyfills
  it so `AppShell` can mount under test.

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
