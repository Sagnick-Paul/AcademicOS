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
