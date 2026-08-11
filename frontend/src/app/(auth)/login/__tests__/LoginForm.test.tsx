import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

// --- Mocks ---------------------------------------------------------------

const replaceMock = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: replaceMock, push: vi.fn(), refresh: vi.fn() }),
}));

const loginMock = vi.fn();
const useAuthMock = vi.fn(() => ({
  login: loginMock,
  // The form only uses login(), but useAuth() returns more — the rest is inert.
  status: "unauthenticated",
  user: null,
  accessToken: null,
  register: vi.fn(),
  logout: vi.fn(),
  refreshUser: vi.fn(),
}));
vi.mock("@/lib/hooks/useAuth", () => ({ useAuth: () => useAuthMock() }));

import { LoginForm } from "../LoginForm";
import { renderWithAuth } from "@/test-utils/wrappers";
import { APIError } from "@/types/api";

beforeEach(() => {
  vi.clearAllMocks();
});

// --- Tests ---------------------------------------------------------------

describe("LoginForm", () => {
  it("submits valid credentials and redirects to /dashboard on success", async () => {
    loginMock.mockResolvedValueOnce(undefined);
    const user = userEvent.setup();
    renderWithAuth(<LoginForm />);

    await user.type(screen.getByLabelText(/email/i), "jane@example.com");
    await user.type(screen.getByLabelText(/password/i), "password123");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(loginMock).toHaveBeenCalledWith({
        email: "jane@example.com",
        password: "password123",
      });
    });
    await waitFor(() => {
      expect(replaceMock).toHaveBeenCalledWith("/dashboard");
    });
  });

  it("shows the backend error on 401 and does NOT redirect", async () => {
    loginMock.mockRejectedValueOnce(
      new APIError("Incorrect email or password", 401),
    );
    const user = userEvent.setup();
    renderWithAuth(<LoginForm />);

    await user.type(screen.getByLabelText(/email/i), "bad@example.com");
    await user.type(screen.getByLabelText(/password/i), "badpass1");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(
        screen.getByText(/incorrect email or password/i),
      ).toBeInTheDocument();
    });
    expect(replaceMock).not.toHaveBeenCalled();
  });

  it("disables the submit button while the request is in flight", async () => {
    let resolveLogin!: () => void;
    loginMock.mockReturnValueOnce(
      new Promise<void>((r) => {
        resolveLogin = r;
      }),
    );
    const user = userEvent.setup();
    renderWithAuth(<LoginForm />);

    await user.type(screen.getByLabelText(/email/i), "jane@example.com");
    await user.type(screen.getByLabelText(/password/i), "password123");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    // Now the button should be in its pending state.
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /signing in/i })).toBeDisabled();
    });

    // Resolve the pending promise so afterEach cleanup is happy.
    resolveLogin();
  });

  it("links to /register for new users", () => {
    renderWithAuth(<LoginForm />);
    const link = screen.getByRole("link", { name: /create an account/i });
    expect(link).toHaveAttribute("href", "/register");
  });
});
