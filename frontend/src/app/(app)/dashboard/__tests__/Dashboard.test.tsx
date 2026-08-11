import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";

// Mock the API modules so we never hit the network. Hoisted so that
// vi.mock factories can reference them.
const { mockDocumentsApi, mockChatApi } = vi.hoisted(() => ({
  mockDocumentsApi: {
    list: vi.fn(),
    upload: vi.fn(),
    get: vi.fn(),
    remove: vi.fn(),
  },
  mockChatApi: {
    oneShot: vi.fn(),
    createSession: vi.fn(),
    listSessions: vi.fn(),
    getSession: vi.fn(),
    updateSession: vi.fn(),
    deleteSession: vi.fn(),
    sendMessage: vi.fn(),
  },
}));
vi.mock("@/lib/api/documents", () => ({ documentsApi: mockDocumentsApi }));
vi.mock("@/lib/api/chat", () => ({ chatApi: mockChatApi }));

import { Dashboard } from "../Dashboard";
import { renderWithAuth } from "@/test-utils/wrappers";
import { APIError } from "@/types/api";
import type { User } from "@/types/user";

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
});

describe("Dashboard", () => {
  it("renders an authenticated greeting using the user's first name", () => {
    mockDocumentsApi.list.mockReturnValue(new Promise(() => {})); // never resolves
    mockChatApi.listSessions.mockReturnValue(new Promise(() => {}));

    renderWithAuth(<Dashboard />, { user: fakeUser });

    // Greeting uses the first name; "Good morning/afternoon/evening" varies.
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(/Jane/);
  });

  it("uses 'there' when there is no user", () => {
    mockDocumentsApi.list.mockReturnValue(new Promise(() => {}));
    mockChatApi.listSessions.mockReturnValue(new Promise(() => {}));

    renderWithAuth(<Dashboard />, { user: null });

    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      /there/,
    );
  });

  it("renders the empty state when both APIs return []", async () => {
    mockDocumentsApi.list.mockResolvedValue([]);
    mockChatApi.listSessions.mockResolvedValue([]);

    renderWithAuth(<Dashboard />, { user: fakeUser });

    await waitFor(() => {
      expect(screen.getByTestId("stat-documents")).toHaveTextContent("0");
      expect(screen.getByTestId("stat-conversations")).toHaveTextContent("0");
    });

    expect(
      screen.getByText(/no recent activity yet/i),
    ).toBeInTheDocument();
  });

  it("renders real API-backed counts when data is present", async () => {
    mockDocumentsApi.list.mockResolvedValue([
      { id: "d1", owner_id: "u1", filename: "a.pdf", original_filename: "a.pdf", file_type: "pdf", file_size: 100, storage_path: "/a.pdf", upload_status: "ready", created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" },
      { id: "d2", owner_id: "u1", filename: "b.pdf", original_filename: "b.pdf", file_type: "pdf", file_size: 200, storage_path: "/b.pdf", upload_status: "ready", created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" },
    ]);
    mockChatApi.listSessions.mockResolvedValue([
      { id: "s1", user_id: "u1", title: "T", created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" },
    ]);

    renderWithAuth(<Dashboard />, { user: fakeUser });

    await waitFor(() => {
      expect(screen.getByTestId("stat-documents")).toHaveTextContent("2");
      expect(screen.getByTestId("stat-conversations")).toHaveTextContent("1");
    });
  });

  it("shows the documents-panel error inline when /documents fails, without crashing the shell", async () => {
    mockDocumentsApi.list.mockRejectedValueOnce(
      new APIError("Network error", 500),
    );
    mockChatApi.listSessions.mockResolvedValue([]);

    renderWithAuth(<Dashboard />, { user: fakeUser });

    await waitFor(() => {
      // The documents stat card surfaces the error message.
      expect(screen.getByTestId("stat-documents")).toHaveTextContent(
        /network error/i,
      );
    });

    // The other panel still renders.
    expect(screen.getByTestId("stat-conversations")).toBeInTheDocument();
    // Quick actions remain available.
    expect(
      screen.getByRole("link", { name: /open documents/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /start a chat/i }),
    ).toBeInTheDocument();
  });

  it("renders Quick Action links to /documents and /chat", async () => {
    mockDocumentsApi.list.mockResolvedValue([]);
    mockChatApi.listSessions.mockResolvedValue([]);

    renderWithAuth(<Dashboard />, { user: fakeUser });

    const docs = screen.getByRole("link", { name: /open documents/i });
    expect(docs).toHaveAttribute("href", "/documents");

    const chat = screen.getByRole("link", { name: /start a chat/i });
    expect(chat).toHaveAttribute("href", "/chat");
  });
});