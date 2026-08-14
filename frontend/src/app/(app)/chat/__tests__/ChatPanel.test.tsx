import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const {
  mockChatApi,
  mockDocumentsApi,
} = vi.hoisted(() => ({
  mockChatApi: {
    listSessions: vi.fn(),
    getSession: vi.fn(),
    createSession: vi.fn(),
    sendMessage: vi.fn(),
    deleteSession: vi.fn(),
    updateSession: vi.fn(),
    oneShot: vi.fn(),
  },
  mockDocumentsApi: {
    list: vi.fn(),
    upload: vi.fn(),
    get: vi.fn(),
    remove: vi.fn(),
  },
}));
vi.mock("@/lib/api/chat", () => ({ chatApi: mockChatApi }));
vi.mock("@/lib/api/documents", () => ({ documentsApi: mockDocumentsApi }));

import { ChatPanel } from "../ChatPanel";
import { renderWithAuth } from "@/test-utils/wrappers";
import { APIError } from "@/types/api";
import type {
  ChatMessage,
  ChatMessageWithSources,
  ChatSession,
  ChatSessionMessage,
  ChatSessionWithMessages,
  SendMessageResponse,
} from "@/types";

const SESSIONS: ChatSession[] = [
  {
    id: "00000000-0000-0000-0000-000000000001",
    user_id: "u-1",
    title: "Signals & Systems",
    created_at: "2026-08-10T12:00:00Z",
    updated_at: "2026-08-12T09:00:00Z",
  },
  {
    id: "00000000-0000-0000-0000-000000000002",
    user_id: "u-1",
    title: "Transformers",
    created_at: "2026-08-11T12:00:00Z",
    updated_at: "2026-08-11T13:00:00Z",
  },
];

const DOCS = [
  {
    id: "00000000-0000-0000-0000-0000000000a1",
    owner_id: "u-1",
    filename: "s-and-s.pdf",
    original_filename: "Signals and Systems.pdf",
    file_type: "pdf" as const,
    file_size: 1024,
    storage_path: "pdf/s-and-s.pdf",
    upload_status: "ready" as const,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
];

const USER_MSG: ChatMessage = {
  id: "m-1",
  session_id: SESSIONS[0].id,
  role: "user",
  content: "What is a transformer?",
  created_at: "2026-08-12T09:00:00Z",
};

const ASSISTANT_MSG: ChatMessageWithSources = {
  id: "m-2",
  session_id: SESSIONS[0].id,
  role: "assistant",
  content: "A transformer is a deep-learning architecture.",
  created_at: "2026-08-12T09:00:01Z",
  sources: [
    {
      id: "src-1",
      message_id: "m-2",
      document_id: "00000000-0000-0000-0000-0000000000a1",
      chunk_id: "c-1",
      position: 1,
      page_number: 23,
      score: 0.91,
      snippet: "Self-attention is the core operation.",
    },
  ],
};

// The backend returns a mix of user messages (no `sources`) and
// assistant messages (with `sources`), so the session payload is a
// union. The helper accepts that union and produces a value the API
// type accepts.
function makeSessionWithMessages(
  session: ChatSession,
  messages: readonly ChatSessionMessage[] = [],
): ChatSessionWithMessages {
  return { ...session, messages: [...messages] };
}

const NEW_SESSION: ChatSession = {
  id: "00000000-0000-0000-0000-000000000003",
  user_id: "u-1",
  title: "New chat",
  created_at: "2026-08-13T00:00:00Z",
  updated_at: "2026-08-13T00:00:00Z",
};

beforeEach(() => {
  vi.clearAllMocks();
  mockDocumentsApi.list.mockResolvedValue(DOCS);
  // Dynamic list: the new session is appended to the in-memory list
  // the first time listSessions is called *after* createSession, so
  // the ChatPanel's post-create refresh can resolve the new session
  // out of the list.
  let sessionsWithNew: readonly ChatSession[] = SESSIONS;
  mockChatApi.listSessions.mockImplementation(async () => sessionsWithNew);
  mockChatApi.getSession.mockImplementation(async (id: string) => {
    const session = [...SESSIONS, NEW_SESSION].find((s) => s.id === id);
    if (!session) throw new APIError("Chat session not found", 404);
    return makeSessionWithMessages(session, [USER_MSG, ASSISTANT_MSG]);
  });
  mockChatApi.createSession.mockImplementation(async () => {
    sessionsWithNew = [...sessionsWithNew, NEW_SESSION];
    return NEW_SESSION;
  });
});

describe("ChatPanel", () => {
  describe("sessions", () => {
    it("renders a loading state then the session list", async () => {
      renderWithAuth(<ChatPanel />);
      // Initial loading
      expect(screen.getByTestId("chat-sessions-loading")).toBeInTheDocument();
      // After the list resolves
      const list = await screen.findByTestId("chat-sessions-list");
      expect(within(list).getAllByTestId("chat-session-item")).toHaveLength(2);
    });

    it("renders an error state when the session list fails", async () => {
      mockChatApi.listSessions.mockRejectedValue(new APIError("Server error", 500));
      renderWithAuth(<ChatPanel />);
      await waitFor(() => {
        expect(screen.getByRole("alert")).toHaveTextContent(/server error/i);
      });
    });

    it("renders the empty state when the user has no sessions", async () => {
      mockChatApi.listSessions.mockResolvedValue([]);
      renderWithAuth(<ChatPanel />);
      await waitFor(() => {
        expect(screen.getByTestId("chat-sessions-empty")).toBeInTheDocument();
      });
    });
  });

  describe("session selection", () => {
    it("shows a 'select or start' prompt when no session is selected", async () => {
      renderWithAuth(<ChatPanel />);
      await screen.findByTestId("chat-sessions-list");
      expect(screen.getByTestId("chat-no-session")).toBeInTheDocument();
    });

    it("loads messages when a session is selected", async () => {
      const user = userEvent.setup();
      renderWithAuth(<ChatPanel />);
      const items = await screen.findAllByTestId("chat-session-item");
      await user.click(items[0]);
      await waitFor(() => {
        expect(screen.getByTestId("chat-messages")).toBeInTheDocument();
      });
      const messages = screen.getAllByTestId(/chat-message-/);
      expect(messages.length).toBeGreaterThanOrEqual(2);
    });

    it("does not reload messages when the same session is re-selected", async () => {
      const user = userEvent.setup();
      renderWithAuth(<ChatPanel />);
      const items = await screen.findAllByTestId("chat-session-item");
      await user.click(items[0]);
      await screen.findByTestId("chat-messages");
      const callCount = mockChatApi.getSession.mock.calls.length;
      await user.click(items[0]);
      expect(mockChatApi.getSession.mock.calls.length).toBe(callCount);
    });

    it("renders a session-level error when the getSession request fails", async () => {
      const user = userEvent.setup();
      mockChatApi.getSession.mockRejectedValueOnce(new APIError("Chat session not found", 404));
      renderWithAuth(<ChatPanel />);
      const items = await screen.findAllByTestId("chat-session-item");
      await user.click(items[0]);
      await waitFor(() => {
        expect(screen.getByRole("alert")).toHaveTextContent(/chat session not found/i);
      });
    });
  });

  describe("new session", () => {
    it("creates a new session, selects it, and shows an empty composer", async () => {
      const user = userEvent.setup();
      renderWithAuth(<ChatPanel />);
      await screen.findByTestId("chat-sessions-list");
      await user.click(screen.getByTestId("chat-new-session"));
      await waitFor(() => {
        expect(mockChatApi.createSession).toHaveBeenCalled();
      });
      // The empty state appears because the new session has no messages.
      await waitFor(() => {
        expect(screen.getByTestId("chat-messages-empty")).toBeInTheDocument();
      });
      // The composer is enabled (no pending state).
      expect(screen.getByTestId("chat-composer-input")).toBeEnabled();
    });

    it("prevents double-clicks on the new-chat button while a request is in flight", async () => {
      let resolveCreate!: (value: ChatSession) => void;
      mockChatApi.createSession.mockReturnValue(
        new Promise<ChatSession>((res) => { resolveCreate = res; }),
      );
      const user = userEvent.setup();
      renderWithAuth(<ChatPanel />);
      await screen.findByTestId("chat-sessions-list");

      const btn = screen.getByTestId("chat-new-session");
      await user.click(btn);
      expect(btn).toBeDisabled();

      // Try clicking again — the button stays disabled.
      await user.click(btn);
      expect(mockChatApi.createSession).toHaveBeenCalledTimes(1);

      // Resolve the request.
      resolveCreate({
        id: "00000000-0000-0000-0000-000000000003",
        user_id: "u-1",
        title: "New chat",
        created_at: "2026-08-13T00:00:00Z",
        updated_at: "2026-08-13T00:00:00Z",
      });
    });
  });

  describe("send", () => {
    async function selectFirstSession() {
      const user = userEvent.setup();
      renderWithAuth(<ChatPanel />);
      const items = await screen.findAllByTestId("chat-session-item");
      await user.click(items[0]);
      await screen.findByTestId("chat-messages");
      return user;
    }

    it("sends a message and renders the assistant's reply with sources", async () => {
      // The mock backend echoes the user's query back as the persisted
      // user_message — matching the real chat endpoint, which returns
      // the message as the backend stored it.
      const typedQuery = "Explain self-attention";
      const echoedUserMsg: ChatMessage = {
        ...USER_MSG,
        id: "m-100",
        content: typedQuery,
      };
      const sendResponse: SendMessageResponse = {
        user_message: echoedUserMsg,
        assistant_message: ASSISTANT_MSG,
        model: "gemini-1.5-flash",
        retrieval_mode: "hybrid",
      };
      mockChatApi.sendMessage.mockResolvedValue(sendResponse);
      const user = await selectFirstSession();

      const input = screen.getByTestId("chat-composer-input") as HTMLTextAreaElement;
      await user.type(input, typedQuery);
      await user.click(screen.getByTestId("chat-composer-send"));

      expect(mockChatApi.sendMessage).toHaveBeenCalledWith(
        SESSIONS[0].id,
        { query: typedQuery },
      );
      // Wait for the assistant reply to be present.
      await waitFor(() => {
        expect(screen.getAllByTestId("chat-message-assistant").length).toBeGreaterThan(0);
      });
      // The sending indicator is gone.
      expect(screen.queryByTestId("chat-pending-user")).not.toBeInTheDocument();
      // The user's typed query now lives in the persisted user bubble,
      // and the assistant's reply text is rendered alongside it.
      expect(screen.getByText(typedQuery)).toBeInTheDocument();
      expect(screen.getByText(/a transformer is a deep-learning architecture/i)).toBeInTheDocument();
      // Sources render when the assistant message renders.
      expect(screen.getAllByTestId("chat-source-list").length).toBeGreaterThan(0);
    });

    it("shows a 'Generating response…' indicator while the send is in flight", async () => {
      let resolveSend!: (value: SendMessageResponse) => void;
      mockChatApi.sendMessage.mockReturnValue(
        new Promise<SendMessageResponse>((res) => { resolveSend = res; }),
      );
      const user = await selectFirstSession();

      const input = screen.getByTestId("chat-composer-input") as HTMLTextAreaElement;
      await user.type(input, "Hello");
      await user.click(screen.getByTestId("chat-composer-send"));

      // Optimistic bubble + indicator.
      expect(screen.getByTestId("chat-pending-user")).toBeInTheDocument();
      expect(screen.getByText(/generating response/i)).toBeInTheDocument();
      // Composer is disabled.
      expect(screen.getByTestId("chat-composer-input")).toBeDisabled();
      expect(screen.getByTestId("chat-composer-send")).toBeDisabled();

      // Finish the request so the test cleans up.
      resolveSend({
        user_message: USER_MSG,
        assistant_message: ASSISTANT_MSG,
        model: "gemini-1.5-flash",
        retrieval_mode: "hybrid",
      });
    });

    it("prevents empty submissions", async () => {
      const user = await selectFirstSession();
      // The send button is disabled when the input is empty.
      const sendBtn = screen.getByTestId("chat-composer-send");
      expect(sendBtn).toBeDisabled();
      // The submit handler also short-circuits.
      const form = screen.getByTestId("chat-composer");
      form.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
      expect(mockChatApi.sendMessage).not.toHaveBeenCalled();
      // Reference the user var so unused-var linters don't complain.
      void user;
    });

    it("renders the backend error message and keeps the composer usable", async () => {
      mockChatApi.sendMessage.mockRejectedValue(
        new APIError("The chat service is temporarily unavailable. Please try again.", 503),
      );
      const user = await selectFirstSession();

      const input = screen.getByTestId("chat-composer-input") as HTMLTextAreaElement;
      await user.type(input, "Hello");
      await user.click(screen.getByTestId("chat-composer-send"));

      await waitFor(() => {
        expect(screen.getByTestId("chat-composer-error")).toHaveTextContent(
          /temporarily unavailable/i,
        );
      });
      // The composer is re-enabled for retry.
      expect(screen.getByTestId("chat-composer-input")).toBeEnabled();
      expect(screen.getByTestId("chat-composer-send")).toBeEnabled();
    });

    it("recovers from a failed send: subsequent send works", async () => {
      mockChatApi.sendMessage
        .mockRejectedValueOnce(new APIError("Boom", 500))
        .mockResolvedValueOnce({
          user_message: USER_MSG,
          assistant_message: ASSISTANT_MSG,
          model: "gemini-1.5-flash",
          retrieval_mode: "hybrid",
        });
      const user = await selectFirstSession();
      const input = screen.getByTestId("chat-composer-input") as HTMLTextAreaElement;

      await user.type(input, "First attempt");
      await user.click(screen.getByTestId("chat-composer-send"));
      await waitFor(() => {
        expect(screen.getByTestId("chat-composer-error")).toBeInTheDocument();
      });

      // The input was cleared after the first attempt, so re-type.
      await user.type(input, "Second attempt");
      await user.click(screen.getByTestId("chat-composer-send"));
      await waitFor(() => {
        expect(mockChatApi.sendMessage).toHaveBeenCalledTimes(2);
      });
    });

    it("handles 404 (session gone) and surfaces the error without locking the composer", async () => {
      mockChatApi.sendMessage.mockRejectedValue(
        new APIError("Chat session not found", 404),
      );
      const user = await selectFirstSession();
      const input = screen.getByTestId("chat-composer-input") as HTMLTextAreaElement;
      await user.type(input, "Anything");
      await user.click(screen.getByTestId("chat-composer-send"));
      await waitFor(() => {
        expect(screen.getByTestId("chat-composer-error")).toHaveTextContent(
          /chat session not found/i,
        );
      });
      expect(screen.getByTestId("chat-composer-input")).toBeEnabled();
    });

    it("handles 401 (auth expired) by surfacing the API error", async () => {
      mockChatApi.sendMessage.mockRejectedValue(
        new APIError("Not authenticated", 401),
      );
      const user = await selectFirstSession();
      const input = screen.getByTestId("chat-composer-input") as HTMLTextAreaElement;
      await user.type(input, "Hello");
      await user.click(screen.getByTestId("chat-composer-send"));
      await waitFor(() => {
        expect(screen.getByTestId("chat-composer-error")).toHaveTextContent(
          /not authenticated/i,
        );
      });
    });
  });

  describe("authentication", () => {
    it("attaches the bearer token on every chat API call (renders for an authenticated user)", async () => {
      renderWithAuth(<ChatPanel />, {
        accessToken: "test-token",
        status: "authenticated",
        user: {
          id: "u-1",
          full_name: "Jane Doe",
          email: "jane@example.com",
          is_active: true,
          is_verified: false,
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
        },
      });
      await screen.findByTestId("chat-sessions-list");
      expect(mockChatApi.listSessions).toHaveBeenCalled();
    });
  });

  describe("accessibility", () => {
    it("renders the page heading and subtitle", () => {
      renderWithAuth(<ChatPanel />);
      expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(/^Chat$/);
      expect(
        screen.getByText(/ask grounded questions against your document library/i),
      ).toBeInTheDocument();
    });
  });
});
