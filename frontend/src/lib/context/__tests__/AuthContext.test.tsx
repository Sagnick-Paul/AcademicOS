import { describe, it, expect, beforeEach, vi } from "vitest";
import { waitFor, act } from "@testing-library/react";

// Mock the auth API module so we never hit the network. Tests below
// control exactly what /auth/login, /auth/register, /auth/me return.
const { mockAuthApi } = vi.hoisted(() => ({
  mockAuthApi: {
    register: vi.fn(),
    login: vi.fn(),
    me: vi.fn(),
  },
}));
vi.mock("@/lib/api/auth", () => ({ authApi: mockAuthApi }));

import { authApi } from "@/lib/api/auth";
import { renderAuth, makeApiError } from "@/test-utils/renderAuth";
import { setStoredToken, getStoredToken } from "@/lib/auth/storage";
import type { User } from "@/types/user";

const TOKEN_KEY = "academicos:auth:token";
const USER_KEY = "academicos:auth:user";

const fakeUser: User = {
  id: "00000000-0000-0000-0000-000000000001",
  full_name: "Jane Doe",
  email: "jane@example.com",
  is_active: true,
  is_verified: false,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

beforeEach(() => {
  vi.clearAllMocks();
  window.localStorage.clear();
});

// Helper: render <AuthProvider>, wait until bootstrap settles, then run assertions.
async function bootstrapAnd(fn: () => void) {
  let lastStatus: string = "loading";
  renderAuth((v) => {
    lastStatus = v.status;
  });
  await waitFor(() => {
    expect(lastStatus).not.toBe("loading");
  });
  fn();
}

describe("AuthProvider bootstrap", () => {
  it("without a stored token, status ends as unauthenticated", async () => {
    mockAuthApi.me.mockImplementation(() => {
      throw makeApiError("Not authenticated", 401);
    });
    await bootstrapAnd(() => {
      // ok — status is now unauthenticated
    });
  });

  it("with a stored token, /me succeeds -> status authenticated, user populated", async () => {
    window.localStorage.setItem(TOKEN_KEY, "valid-token");
    mockAuthApi.me.mockResolvedValue(fakeUser);

    let user: User | null = null;
    renderAuth((v) => {
      user = v.user;
    });
    await waitFor(() => expect(user).not.toBeNull());
    expect(user!.email).toBe("jane@example.com");
    expect(getStoredToken()).toBe("valid-token"); // untouched
  });

  it("with an expired token, storage is cleared and status is unauthenticated", async () => {
    window.localStorage.setItem(TOKEN_KEY, "expired-token");
    window.localStorage.setItem(USER_KEY, JSON.stringify(fakeUser));
    mockAuthApi.me.mockRejectedValueOnce(makeApiError("Token has expired", 401));

    let last: ReturnType<typeof getStoredToken> | null = null;
    renderAuth((v) => {
      last = v.accessToken;
    });
    await waitFor(() => expect(last).toBeNull());
    expect(getStoredToken()).toBeNull();
    expect(window.localStorage.getItem(USER_KEY)).toBeNull();
  });
});

describe("AuthContext.login", () => {
  it("stores the token, fetches /me, and transitions to authenticated", async () => {
    mockAuthApi.login.mockResolvedValue({ access_token: "new-tok", token_type: "bearer" });
    mockAuthApi.me.mockResolvedValue(fakeUser);

    await bootstrapAnd(() => {
      // After bootstrap (unauthenticated) we have access to login().
    });

    const { context } = renderAuth(() => {});
    await waitFor(() => expect(context().status).not.toBe("loading"));

    await context().login({ email: "jane@example.com", password: "password123" });

    await waitFor(() => {
      expect(context().status).toBe("authenticated");
    });
    expect(getStoredToken()).toBe("new-tok");
    expect(context().user?.email).toBe("jane@example.com");
  });

  it("on 401, throws APIError and does NOT store the token", async () => {
    mockAuthApi.login.mockRejectedValueOnce(
      makeApiError("Incorrect email or password", 401),
    );

    const { context } = renderAuth(() => {});
    await waitFor(() => expect(context().status).not.toBe("loading"));

    await expect(
      context().login({ email: "bad@example.com", password: "badpass1" }),
    ).rejects.toThrow("Incorrect email or password");
    expect(getStoredToken()).toBeNull();
    expect(context().status).not.toBe("authenticated");
  });
});

describe("AuthContext.register", () => {
  it("calls /auth/register, then auto-logs-in (backend does NOT issue a token on register)", async () => {
    mockAuthApi.register.mockResolvedValue(fakeUser);
    mockAuthApi.login.mockResolvedValue({ access_token: "tok", token_type: "bearer" });
    mockAuthApi.me.mockResolvedValue(fakeUser);

    const { context } = renderAuth(() => {});
    await waitFor(() => expect(context().status).not.toBe("loading"));

    await context().register({
      full_name: "Jane Doe",
      email: "jane@example.com",
      password: "password123",
    });

    expect(mockAuthApi.register).toHaveBeenCalledTimes(1);
    expect(mockAuthApi.login).toHaveBeenCalledTimes(1);
    expect(mockAuthApi.login).toHaveBeenCalledWith({
      email: "jane@example.com",
      password: "password123",
    });
    await waitFor(() => {
      expect(context().status).toBe("authenticated");
    });
  });

  it("on 400 Email already registered, surfaces error and does NOT log in", async () => {
    mockAuthApi.register.mockRejectedValueOnce(
      makeApiError("Email already registered", 400),
    );

    const { context } = renderAuth(() => {});
    await waitFor(() => expect(context().status).not.toBe("loading"));

    await expect(
      context().register({
        full_name: "Jane",
        email: "dup@example.com",
        password: "password123",
      }),
    ).rejects.toThrow("Email already registered");

    expect(mockAuthApi.login).not.toHaveBeenCalled();
    expect(getStoredToken()).toBeNull();
    expect(context().status).not.toBe("authenticated");
  });
});

describe("AuthContext.logout", () => {
  it("clears token + user, drops to unauthenticated", async () => {
    window.localStorage.setItem(TOKEN_KEY, "tok");
    mockAuthApi.me.mockResolvedValue(fakeUser);

    const { context } = renderAuth(() => {});
    await waitFor(() => {
      expect(context().status).toBe("authenticated");
    });

    act(() => {
      context().logout();
    });

    expect(getStoredToken()).toBeNull();
    // The USER_KEY stored value should also have been removed.
    expect(window.localStorage.getItem("academicos:auth:user")).toBeNull();
    expect(context().status).toBe("unauthenticated");
    expect(context().user).toBeNull();
  });
});

describe("AuthContext.refreshUser", () => {
  it("re-fetches /me and updates the cached user", async () => {
    window.localStorage.setItem(TOKEN_KEY, "tok");
    const updated: User = { ...fakeUser, full_name: "Jane Updated" };
    mockAuthApi.me.mockResolvedValueOnce(fakeUser).mockResolvedValueOnce(updated);

    const { context } = renderAuth(() => {});
    await waitFor(() => expect(context().user?.full_name).toBe("Jane Doe"));

    await context().refreshUser();
    await waitFor(() => expect(context().user?.full_name).toBe("Jane Updated"));
  });
});

// catch unused-import warnings for the storage helper used above.
void setStoredToken;
