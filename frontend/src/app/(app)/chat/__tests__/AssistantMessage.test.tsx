import { describe, it, expect, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { AssistantMessage } from "../components/AssistantMessage";
import type { ChatMessageSource, ChatMessageWithSources } from "@/types";

function makeAssistant(overrides: Partial<ChatMessageWithSources> = {}): ChatMessageWithSources {
  return {
    id: "m-1",
    session_id: "s-1",
    role: "assistant",
    content: "Transformers use self-attention.",
    created_at: "2026-08-12T09:00:00Z",
    sources: [],
    ...overrides,
  };
}

const SOURCES: ChatMessageSource[] = [
  {
    id: "src-1",
    message_id: "m-1",
    document_id: "doc-1",
    chunk_id: "c-1",
    position: 1,
    page_number: 23,
    score: 0.91,
    snippet: "Self-attention allows the model to weigh tokens.",
  },
  {
    id: "src-2",
    message_id: "m-1",
    document_id: "doc-2",
    chunk_id: "c-2",
    position: 2,
    page_number: 41,
    score: 0.84,
    snippet: "Multi-head attention splits queries, keys, values.",
  },
];

describe("AssistantMessage", () => {
  it("renders the assistant's content", () => {
    render(
      <AssistantMessage
        message={makeAssistant()}
        documentTitles={new Map()}
      />,
    );
    expect(screen.getByTestId("chat-message-assistant")).toHaveTextContent(
      /transformers use self-attention/i,
    );
  });

  it("does not render a source list when there are no sources", () => {
    render(
      <AssistantMessage
        message={makeAssistant({ sources: [] })}
        documentTitles={new Map()}
      />,
    );
    expect(screen.queryByTestId("chat-source-list")).not.toBeInTheDocument();
  });

  it("renders the source toggle collapsed by default", () => {
    render(
      <AssistantMessage
        message={makeAssistant({ sources: SOURCES })}
        documentTitles={new Map()}
      />,
    );
    const toggle = screen.getByTestId("chat-source-toggle");
    expect(toggle).toHaveTextContent(/sources \(2\)/i);
    expect(screen.queryByTestId("chat-source-items")).not.toBeInTheDocument();
  });

  it("expands to show source metadata when the toggle is clicked", async () => {
    const titles = new Map([
      ["doc-1", "Signals and Systems.pdf"],
      ["doc-2", "Electrical Machines Notes.pdf"],
    ]);
    const user = userEvent.setup();
    render(
      <AssistantMessage
        message={makeAssistant({ sources: SOURCES })}
        documentTitles={titles}
      />,
    );
    await user.click(screen.getByTestId("chat-source-toggle"));
    const items = screen.getAllByTestId("chat-source-item");
    expect(items).toHaveLength(2);

    const first = items[0];
    expect(within(first).getByText("[1]")).toBeInTheDocument();
    expect(within(first).getByText("Signals and Systems.pdf")).toBeInTheDocument();
    expect(within(first).getByText(/page 23/i)).toBeInTheDocument();
    expect(within(first).getByText(/score 0\.91/i)).toBeInTheDocument();
    expect(within(first).getByText(/self-attention/i)).toBeInTheDocument();
  });

  it("falls back to 'Untitled document' when the document is not in the user's library", async () => {
    const user = userEvent.setup();
    render(
      <AssistantMessage
        message={makeAssistant({ sources: SOURCES })}
        documentTitles={new Map()}
      />,
    );
    await user.click(screen.getByTestId("chat-source-toggle"));
    const items = screen.getAllByTestId("chat-source-item");
    items.forEach((item) => {
      expect(within(item).getByText(/untitled document/i)).toBeInTheDocument();
    });
  });

  it("collapses the source list when the toggle is clicked again", async () => {
    const user = userEvent.setup();
    render(
      <AssistantMessage
        message={makeAssistant({ sources: SOURCES })}
        documentTitles={new Map()}
      />,
    );
    const toggle = screen.getByTestId("chat-source-toggle");
    await user.click(toggle);
    expect(screen.getByTestId("chat-source-items")).toBeInTheDocument();
    await user.click(toggle);
    expect(screen.queryByTestId("chat-source-items")).not.toBeInTheDocument();
  });
});
