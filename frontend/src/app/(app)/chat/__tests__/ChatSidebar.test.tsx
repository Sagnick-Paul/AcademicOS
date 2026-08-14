import { describe, it, expect, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ChatSidebar } from "../components/ChatSidebar";
import type { ChatSession } from "@/types";

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

describe("ChatSidebar", () => {
  it("renders a loading state while sessions are loading", () => {
    render(
      <ChatSidebar
        status="loading"
        error={null}
        sessions={[]}
        selectedSessionId={null}
        creating={false}
        onSelectSession={vi.fn()}
        onCreateSession={vi.fn()}
      />,
    );
    expect(screen.getByTestId("chat-sessions-loading")).toBeInTheDocument();
  });

  it("renders an error state when the session list fails", () => {
    render(
      <ChatSidebar
        status="error"
        error="Network down"
        sessions={[]}
        selectedSessionId={null}
        creating={false}
        onSelectSession={vi.fn()}
        onCreateSession={vi.fn()}
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent(/network down/i);
  });

  it("renders the empty state when there are no sessions", () => {
    render(
      <ChatSidebar
        status="ready"
        error={null}
        sessions={[]}
        selectedSessionId={null}
        creating={false}
        onSelectSession={vi.fn()}
        onCreateSession={vi.fn()}
      />,
    );
    expect(screen.getByTestId("chat-sessions-empty")).toBeInTheDocument();
  });

  it("renders a row for every session returned by the backend", () => {
    render(
      <ChatSidebar
        status="ready"
        error={null}
        sessions={SESSIONS}
        selectedSessionId={null}
        creating={false}
        onSelectSession={vi.fn()}
        onCreateSession={vi.fn()}
      />,
    );
    const list = screen.getByTestId("chat-sessions-list");
    const items = within(list).getAllByTestId("chat-session-item");
    expect(items).toHaveLength(2);
    expect(within(list).getByText("Signals & Systems")).toBeInTheDocument();
    expect(within(list).getByText("Transformers")).toBeInTheDocument();
  });

  it("marks the currently selected session", () => {
    render(
      <ChatSidebar
        status="ready"
        error={null}
        sessions={SESSIONS}
        selectedSessionId={SESSIONS[0].id}
        creating={false}
        onSelectSession={vi.fn()}
        onCreateSession={vi.fn()}
      />,
    );
    const items = screen.getAllByTestId("chat-session-item");
    expect(items[0]).toHaveAttribute("aria-current", "true");
    expect(items[1]).toHaveAttribute("aria-current", "false");
  });

  it("invokes onSelectSession with the right session when a row is clicked", async () => {
    const onSelect = vi.fn();
    const user = userEvent.setup();
    render(
      <ChatSidebar
        status="ready"
        error={null}
        sessions={SESSIONS}
        selectedSessionId={null}
        creating={false}
        onSelectSession={onSelect}
        onCreateSession={vi.fn()}
      />,
    );
    await user.click(screen.getAllByTestId("chat-session-item")[1]);
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith(SESSIONS[1]);
  });

  it("invokes onCreateSession when '+ New chat' is clicked", async () => {
    const onCreate = vi.fn();
    const user = userEvent.setup();
    render(
      <ChatSidebar
        status="ready"
        error={null}
        sessions={SESSIONS}
        selectedSessionId={null}
        creating={false}
        onSelectSession={vi.fn()}
        onCreateSession={onCreate}
      />,
    );
    await user.click(screen.getByTestId("chat-new-session"));
    expect(onCreate).toHaveBeenCalledTimes(1);
  });

  it("disables the new-chat button while creating is true", () => {
    render(
      <ChatSidebar
        status="ready"
        error={null}
        sessions={SESSIONS}
        selectedSessionId={null}
        creating={true}
        onSelectSession={vi.fn()}
        onCreateSession={vi.fn()}
      />,
    );
    const btn = screen.getByTestId("chat-new-session");
    expect(btn).toBeDisabled();
    expect(btn).toHaveTextContent(/creating/i);
  });
});
