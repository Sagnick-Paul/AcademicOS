import { describe, it, expect, beforeEach, vi } from "vitest";
import { apiFetch } from "../client";
import { API_PATHS, API_ROOT } from "@/lib/constants/api";
import { APIError } from "@/types/api";

const TOKEN_KEY = "academicos:auth:token";

describe("apiFetch", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.restoreAllMocks();
  });

  it("sends Authorization: Bearer <token> when a token is in storage", async () => {
    window.localStorage.setItem(TOKEN_KEY, "abc.def.ghi");
    const fetchSpy = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchSpy);

    await apiFetch("/test", { auth: true });

    const [, init] = fetchSpy.mock.calls[0];
    const headers = (init as RequestInit).headers as Record<string, string>;
    expect(headers.Authorization).toBe("Bearer abc.def.ghi");
  });

  it("omits Authorization when auth:false (login/register)", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({}), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchSpy);

    await apiFetch(API_PATHS.auth.login, {
      method: "POST",
      body: { email: "a@b.c", password: "password" },
      auth: false,
    });

    const [, init] = fetchSpy.mock.calls[0];
    const headers = (init as RequestInit).headers as Record<string, string>;
    expect(headers.Authorization).toBeUndefined();
    expect(headers["Content-Type"]).toBe("application/json");
  });

  it("hits API_ROOT + path", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({}), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchSpy);

    await apiFetch(API_PATHS.auth.me, { auth: false });
    const [url] = fetchSpy.mock.calls[0];
    expect(url).toBe(`${API_ROOT}/auth/me`);
  });

  it("normalizes 401 with string detail to APIError", async () => {
    // mockImplementation lets multiple calls in one test return the same body
    // (mockResolvedValue only fires once per .mock.calls index).
    const fetchSpy = vi.fn().mockImplementation(
      () =>
        new Promise<Response>((resolve) =>
          resolve(
            new Response(
              JSON.stringify({ detail: "Incorrect email or password" }),
              { status: 401 },
            ),
          ),
        ),
    );
    vi.stubGlobal("fetch", fetchSpy);

    let captured: APIError | null = null;
    try {
      await apiFetch(API_PATHS.auth.login, { method: "POST", auth: false });
    } catch (err) {
      captured = err as APIError;
    }
    expect(captured).toBeInstanceOf(APIError);
    expect(captured!.status).toBe(401);
    expect(captured!.message).toBe("Incorrect email or password");
  });

  it("joins 422 validation detail array into a single message", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: [
            { loc: ["body", "password"], msg: "too short", type: "value_error" },
            { loc: ["body", "email"], msg: "invalid", type: "value_error" },
          ],
        }),
        { status: 422 },
      ),
    );
    vi.stubGlobal("fetch", fetchSpy);

    try {
      await apiFetch(API_PATHS.auth.register, { method: "POST", auth: false });
    } catch (err) {
      expect(err).toBeInstanceOf(APIError);
      expect((err as APIError).status).toBe(422);
      expect((err as APIError).message).toContain("too short");
      expect((err as APIError).message).toContain("invalid");
    }
  });

  it("returns undefined on 204 No Content", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchSpy);

    const result = await apiFetch<void>("/anything", { method: "DELETE" });
    expect(result).toBeUndefined();
  });
});
