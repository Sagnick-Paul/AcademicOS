import { describe, it, expect, vi, beforeEach } from "vitest";
import { render } from "@testing-library/react";
import { waitFor } from "@testing-library/react";

const replaceMock = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: replaceMock, push: vi.fn(), refresh: vi.fn() }),
}));

const useAuthMock = vi.fn();
vi.mock("@/lib/hooks/useAuth", () => ({ useAuth: () => useAuthMock() }));

import HomePage from "../page";

beforeEach(() => {
  vi.clearAllMocks();
});

describe("HomePage (root route redirector)", () => {
  it("renders a loading state while auth status is loading", () => {
    useAuthMock.mockReturnValue({ status: "loading" });
    render(<HomePage />);
    expect(replaceMock).not.toHaveBeenCalled();
  });

  it("redirects authenticated users to /dashboard", async () => {
    useAuthMock.mockReturnValue({ status: "authenticated" });
    render(<HomePage />);
    await waitFor(() => {
      expect(replaceMock).toHaveBeenCalledWith("/dashboard");
    });
  });

  it("redirects unauthenticated users to /login", async () => {
    useAuthMock.mockReturnValue({ status: "unauthenticated" });
    render(<HomePage />);
    await waitFor(() => {
      expect(replaceMock).toHaveBeenCalledWith("/login");
    });
  });
});