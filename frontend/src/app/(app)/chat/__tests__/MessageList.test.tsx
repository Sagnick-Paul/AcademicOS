import { describe, it, expect, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";

import { MessageList } from "../components/MessageList";
import type { ChatMessage, ChatMessageWithSources } from "@/types";

const userMsg: ChatMessage = {
  id: "m-1",
  session_id: "s-1",
  role: "user",
  content: "What is a transformer?",
  created_at: "2026-08-12T09:00:00Z",
};

const assistantMsg: ChatMessageWithSources = {
  id: "m-2",
  session_id: "s-1",
  role: "assistant",
  content: "A transformer is a deep-learning architecture based on self-attention.",
  created_at: "2026-08-12T09:00:01Z",
  sources: [],
};

describe("MessageList", () => {
  it("renders a loading state", () => {
    render(<MessageList state={{ status: "loading" }} documentTitles={new Map()} />);
    expect(screen.getByTestId("chat-messages-loading")).toBeInTheDocument();
  });

  it("renders an error state", () => {
    render(
      <MessageList
        state={{ status: "error", message: "Backend down" }}
        documentTitles={new Map()}
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent(/backend down/i);
  });

  it("renders the empty state when there are no messages", () => {
    render(
      <MessageList state={{ status: "ready", messages: [] }} documentTitles={new Map()} />,
    );
    expect(screen.getByTestId("chat-messages-empty")).toBeInTheDocument();
  });

  it("renders user and assistant messages in the order returned by the backend", () => {
    render(
      <MessageList
        state={{ status: "ready", messages: [userMsg, assistantMsg] }}
        documentTitles={new Map()}
      />,
    );
    const list = screen.getByTestId("chat-messages");
    const items = within(list).getAllByTestId(/chat-message-/);
    expect(items[0]).toHaveAttribute("data-testid", "chat-message-user");
    expect(items[1]).toHaveAttribute("data-testid", "chat-message-assistant");
  });

  it("renders an optimistic user message with a 'Generating response…' indicator while a send is pending", () => {
    render(
      <MessageList
        state={{ status: "ready", messages: [userMsg, assistantMsg] }}
        pendingUserMessage="Follow-up question"
        documentTitles={new Map()}
      />,
    );
    expect(screen.getByTestId("chat-pending-user")).toBeInTheDocument();
    expect(screen.getByText(/generating response/i)).toBeInTheDocument();
  });
});
