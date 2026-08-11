import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

const replaceMock = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: replaceMock, push: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/dashboard",
}));

const useAuthMock = vi.fn();
vi.mock("@/lib/hooks/useAuth", () => ({ useAuth: () => useAuthMock() }));

import AppLayout from "../layout";

beforeEach(() => {
  vi.clearAllMocks();
});

describe("(app)/layout", () => {
  it("renders a loading state while status is loading", () => {
    useAuthMock.mockReturnValue({ status: "loading", user: null });
    render(
      <AppLayout>
        <div data-testid="protected-child">child</div>
      </AppLayout>,
    );
    expect(screen.queryByTestId("protected-child")).not.toBeInTheDocument();
    expect(replaceMock).not.toHaveBeenCalled();
  });

  it("redirects unauthenticated users to /login and does not render protected content", async () => {
    useAuthMock.mockReturnValue({ status: "unauthenticated", user: null });
    render(
      <AppLayout>
        <div data-testid="protected-child">child</div>
      </AppLayout>,
    );
    await waitFor(() => {
      expect(replaceMock).toHaveBeenCalledWith("/login");
    });
    expect(screen.queryByTestId("protected-child")).not.toBeInTheDocument();
  });

  it("renders children inside AppShell when authenticated", () => {
    useAuthMock.mockReturnValue({
      status: "authenticated",
      user: {
        id: "u1",
        full_name: "Jane",
        email: "jane@example.com",
        is_active: true,
        is_verified: false,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
      },
    });
    render(
      <AppLayout>
        <div data-testid="protected-child">child</div>
      </AppLayout>,
    );
    expect(screen.getByTestId("protected-child")).toBeInTheDocument();
    expect(replaceMock).not.toHaveBeenCalled();
  });
});