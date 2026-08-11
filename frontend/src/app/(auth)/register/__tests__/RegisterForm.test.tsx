import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

// --- Mocks ---------------------------------------------------------------

const replaceMock = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: replaceMock, push: vi.fn(), refresh: vi.fn() }),
}));

const registerMock = vi.fn();
const useAuthMock = vi.fn(() => ({
  register: registerMock,
  status: "unauthenticated",
  user: null,
  accessToken: null,
  login: vi.fn(),
  logout: vi.fn(),
  refreshUser: vi.fn(),
}));
vi.mock("@/lib/hooks/useAuth", () => ({ useAuth: () => useAuthMock() }));

import { RegisterForm } from "../RegisterForm";
import { renderWithAuth } from "@/test-utils/wrappers";
import { APIError } from "@/types/api";

beforeEach(() => {
  vi.clearAllMocks();
});

describe("RegisterForm", () => {
  it("submits full_name + email + password, redirects to /dashboard", async () => {
    registerMock.mockResolvedValueOnce(undefined);
    const user = userEvent.setup();
    renderWithAuth(<RegisterForm />);

    await user.type(screen.getByLabelText(/full name/i), "Jane Doe");
    await user.type(screen.getByLabelText(/email/i), "jane@example.com");
    await user.type(screen.getByLabelText(/password/i), "password123");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(registerMock).toHaveBeenCalledWith({
        full_name: "Jane Doe",
        email: "jane@example.com",
        password: "password123",
      });
    });
    await waitFor(() => {
      expect(replaceMock).toHaveBeenCalledWith("/dashboard");
    });
  });

  it("shows backend error on 400 (duplicate email) and does NOT redirect", async () => {
    registerMock.mockRejectedValueOnce(
      new APIError("Email already registered", 400),
    );
    const user = userEvent.setup();
    renderWithAuth(<RegisterForm />);

    await user.type(screen.getByLabelText(/full name/i), "Jane");
    await user.type(screen.getByLabelText(/email/i), "dup@example.com");
    await user.type(screen.getByLabelText(/password/i), "password123");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(screen.getByText(/email already registered/i)).toBeInTheDocument();
    });
    expect(replaceMock).not.toHaveBeenCalled();
  });

  it("disables the submit button while the request is in flight", async () => {
    let resolveRegister!: () => void;
    registerMock.mockReturnValueOnce(
      new Promise<void>((r) => {
        resolveRegister = r;
      }),
    );
    const user = userEvent.setup();
    renderWithAuth(<RegisterForm />);

    await user.type(screen.getByLabelText(/full name/i), "Jane Doe");
    await user.type(screen.getByLabelText(/email/i), "jane@example.com");
    await user.type(screen.getByLabelText(/password/i), "password123");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /creating/i })).toBeDisabled();
    });
    resolveRegister();
  });

  it("links to /login for existing accounts", () => {
    renderWithAuth(<RegisterForm />);
    const link = screen.getByRole("link", { name: /sign in/i });
    expect(link).toHaveAttribute("href", "/login");
  });
});
