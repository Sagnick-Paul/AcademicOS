import { describe, it, expect, beforeEach, vi } from "vitest";
import { authApi } from "../auth";
import { API_PATHS, API_ROOT } from "@/lib/constants/api";

// authApi is a thin wrapper over apiFetch. We test it as a contract:
// correct path, correct HTTP method, correct payload shape.

function mockJsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("authApi", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    window.localStorage.clear();
  });

  describe("register", () => {
    it("POSTs to /auth/register with auth:false", async () => {
      const fetchSpy = vi.fn().mockResolvedValue(
        mockJsonResponse({
          id: "00000000-0000-0000-0000-000000000001",
          full_name: "Jane Doe",
          email: "jane@example.com",
          is_active: true,
          is_verified: false,
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
        }, 201),
      );
      vi.stubGlobal("fetch", fetchSpy);

      const user = await authApi.register({
        full_name: "Jane Doe",
        email: "jane@example.com",
        password: "password123",
      });

      const [url, init] = fetchSpy.mock.calls[0];
      expect(url).toBe(`${API_ROOT}${API_PATHS.auth.register}`);
      expect((init as RequestInit).method).toBe("POST");
      expect(JSON.parse((init as RequestInit).body as string)).toEqual({
        full_name: "Jane Doe",
        email: "jane@example.com",
        password: "password123",
      });
      expect(user.email).toBe("jane@example.com");
    });

    it("surfaces 400 Email already registered", async () => {
      const fetchSpy = vi.fn().mockResolvedValue(
        mockJsonResponse({ detail: "Email already registered" }, 400),
      );
      vi.stubGlobal("fetch", fetchSpy);

      await expect(
        authApi.register({
          full_name: "Jane",
          email: "dup@example.com",
          password: "password123",
        }),
      ).rejects.toThrow("Email already registered");
    });
  });

  describe("login", () => {
    it("POSTs credentials and returns access_token", async () => {
      const fetchSpy = vi.fn().mockResolvedValue(
        mockJsonResponse({ access_token: "tok", token_type: "bearer" }, 200),
      );
      vi.stubGlobal("fetch", fetchSpy);

      const result = await authApi.login({
        email: "jane@example.com",
        password: "password123",
      });

      expect(result.access_token).toBe("tok");
      expect(result.token_type).toBe("bearer");

      const [, init] = fetchSpy.mock.calls[0];
      expect(JSON.parse((init as RequestInit).body as string)).toEqual({
        email: "jane@example.com",
        password: "password123",
      });
    });

    it("surfaces 401 Incorrect email or password", async () => {
      const fetchSpy = vi.fn().mockResolvedValue(
        mockJsonResponse({ detail: "Incorrect email or password" }, 401),
      );
      vi.stubGlobal("fetch", fetchSpy);

      await expect(
        authApi.login({ email: "x@y.z", password: "password123" }),
      ).rejects.toThrow("Incorrect email or password");
    });
  });

  describe("me", () => {
    it("calls /auth/me without explicit body", async () => {
      const fetchSpy = vi.fn().mockResolvedValue(
        mockJsonResponse({
          id: "00000000-0000-0000-0000-000000000001",
          full_name: "Jane",
          email: "jane@example.com",
          is_active: true,
          is_verified: false,
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
        }),
      );
      vi.stubGlobal("fetch", fetchSpy);

      await authApi.me();

      const [url, init] = fetchSpy.mock.calls[0];
      expect(url).toBe(`${API_ROOT}${API_PATHS.auth.me}`);
      expect((init as RequestInit).method).toBe("GET");
    });
  });
});
