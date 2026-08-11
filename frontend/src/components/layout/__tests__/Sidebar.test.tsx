import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";

// next/navigation usePathname drives active state. Mock it.
const mockPathname = vi.fn(() => "/dashboard");
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn(), push: vi.fn(), refresh: vi.fn() }),
  usePathname: () => mockPathname(),
}));

const logoutMock = vi.fn();
const useAuthMock = vi.fn(() => ({
  status: "authenticated",
  user: {
    id: "u1",
    full_name: "Jane Doe",
    email: "jane@example.com",
    is_active: true,
    is_verified: false,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
  accessToken: "tok",
  login: vi.fn(),
  register: vi.fn(),
  logout: logoutMock,
  refreshUser: vi.fn(),
}));
vi.mock("@/lib/hooks/useAuth", () => ({ useAuth: () => useAuthMock() }));

import { Sidebar } from "../Sidebar";
import { renderWithAuth } from "@/test-utils/wrappers";

beforeEach(() => {
  vi.clearAllMocks();
  mockPathname.mockReturnValue("/dashboard");
});

describe("Sidebar", () => {
  it("renders Dashboard / Documents / Chat nav items", () => {
    renderWithAuth(
      <div>
        <Sidebar open={false} onClose={() => undefined} />
      </div>,
      {
        user: useAuthMock().user,
      },
    );

    expect(screen.getByRole("link", { name: "Dashboard" })).toHaveAttribute(
      "href",
      "/dashboard",
    );
    expect(screen.getByRole("link", { name: "Documents" })).toHaveAttribute(
      "href",
      "/documents",
    );
    expect(screen.getByRole("link", { name: "Chat" })).toHaveAttribute(
      "href",
      "/chat",
    );
  });

  it("marks the active nav item with aria-current='page'", () => {
    mockPathname.mockReturnValue("/documents");
    renderWithAuth(
      <div>
        <Sidebar open={false} onClose={() => undefined} />
      </div>,
      { user: useAuthMock().user },
    );

    expect(
      screen.getByRole("link", { name: "Documents" }),
    ).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Dashboard" })).not.toHaveAttribute(
      "aria-current",
    );
  });

  it("uses prefix matching for nested routes", () => {
    mockPathname.mockReturnValue("/documents/abc-123/edit");
    renderWithAuth(
      <div>
        <Sidebar open={false} onClose={() => undefined} />
      </div>,
      { user: useAuthMock().user },
    );

    expect(
      screen.getByRole("link", { name: "Documents" }),
    ).toHaveAttribute("aria-current", "page");
  });

  it("shows the authenticated user's full name and email", () => {
    renderWithAuth(
      <div>
        <Sidebar open={false} onClose={() => undefined} />
      </div>,
      { user: useAuthMock().user },
    );

    expect(screen.getByText("Jane Doe")).toBeInTheDocument();
    expect(screen.getByText("jane@example.com")).toBeInTheDocument();
  });

  it("logout button invokes the existing AuthContext.logout()", async () => {
    const { default: userEvent } = await import("@testing-library/user-event");
    const user = userEvent.setup();
    renderWithAuth(
      <div>
        <Sidebar open={false} onClose={() => undefined} />
      </div>,
      { user: useAuthMock().user },
    );

    await user.click(screen.getByRole("button", { name: /sign out/i }));
    expect(logoutMock).toHaveBeenCalledTimes(1);
  });

  it("renders the scrim only when the mobile drawer is open", () => {
    const { rerender } = renderWithAuth(
      <div>
        <Sidebar open={false} onClose={() => undefined} />
      </div>,
      { user: useAuthMock().user },
    );

    expect(
      screen.queryByRole("button", { name: /close navigation/i }),
    ).not.toBeInTheDocument();

    rerender(
      <div>
        <Sidebar open={true} onClose={() => undefined} />
      </div>,
    );

    expect(
      screen.getByRole("button", { name: /close navigation/i }),
    ).toBeInTheDocument();
  });

  it("invokes onClose when a nav link is clicked", async () => {
    const { default: userEvent } = await import("@testing-library/user-event");
    const onClose = vi.fn();
    const user = userEvent.setup();
    renderWithAuth(
      <div>
        <Sidebar open={true} onClose={onClose} />
      </div>,
      { user: useAuthMock().user },
    );

    await user.click(screen.getByRole("link", { name: "Documents" }));
    expect(onClose).toHaveBeenCalled();
  });
});