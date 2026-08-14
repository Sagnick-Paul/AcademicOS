"use client";

import { useEffect, useRef, type ReactNode } from "react";
import { EmptyState } from "@/components/primitives/EmptyState";
import { ErrorState } from "@/components/primitives/ErrorState";
import { LoadingState } from "@/components/primitives/LoadingState";
import type { ChatMessage, ChatMessageWithSources } from "@/types";
import { AssistantMessage } from "./AssistantMessage";
import { UserMessage } from "./UserMessage";
import styles from "./MessageList.module.css";

/** A message as stored in component state. User messages don't
 *  have `sources`; assistant messages always do. */
type StoredMessage = ChatMessage | ChatMessageWithSources;

function isAssistant(msg: StoredMessage): msg is ChatMessageWithSources {
  return msg.role === "assistant";
}

type LoadState =
  | { status: "loading" }
  | { status: "ready"; messages: readonly StoredMessage[] }
  | { status: "error"; message: string };

interface MessageListProps {
  /** Loading / ready / error for the *currently selected* session. */
  state: LoadState;
  /** Optional transient state: a user message that was just sent but whose assistant reply hasn't arrived yet. */
  pendingUserMessage?: string | null;
  documentTitles: ReadonlyMap<string, string>;
}

/**
 * The scrollable message list. Renders messages in the order the
 * backend returned them (chronological — see chat_service._load_history
 * and the repository's `list_for_session` ordering).
 *
 * Auto-scroll behaviour: we only scroll to the bottom when the user
 * is already at (or near) the bottom of the list. If they have
 * scrolled up to read older messages, we leave them alone. This is
 * the standard chat-app pattern.
 */
export function MessageList({ state, pendingUserMessage = null, documentTitles }: MessageListProps) {
  const scrollerRef = useRef<HTMLDivElement>(null);
  const lastMessageCount = useRef(0);
  const wasNearBottom = useRef(true);

  // Track whether the user is near the bottom. Used to decide
  // whether to auto-scroll on new messages.
  useEffect(() => {
    const scroller = scrollerRef.current;
    if (!scroller) return;
    const onScroll = () => {
      const distance = scroller.scrollHeight - scroller.scrollTop - scroller.clientHeight;
      wasNearBottom.current = distance < 80;
    };
    scroller.addEventListener("scroll", onScroll, { passive: true });
    return () => scroller.removeEventListener("scroll", onScroll);
  }, []);

  // Auto-scroll on new content. Only scrolls if the user was already
  // at (or near) the bottom — never yanks the scroll away while
  // they're reading older messages.
  useEffect(() => {
    const scroller = scrollerRef.current;
    if (!scroller) return;
    if (!wasNearBottom.current) return;
    const current = state.status === "ready" ? state.messages.length : 0;
    if (current === lastMessageCount.current && !pendingUserMessage) return;
    scroller.scrollTop = scroller.scrollHeight;
    lastMessageCount.current = current;
  }, [state, pendingUserMessage]);

  let content: ReactNode;
  if (state.status === "loading") {
    content = (
      <div className={styles.centered} data-testid="chat-messages-loading">
        <LoadingState label="Loading messages…" />
      </div>
    );
  } else if (state.status === "error") {
    content = (
      <ErrorState
        title="Could not load messages"
        description={state.message}
      />
    );
  } else if (state.messages.length === 0) {
    // Empty state lives here so the layout doesn't jump.
    return (
      <div className={styles.scroller} data-testid="chat-messages-empty">
        <EmptyState
          title="Ask something about your academic material"
          description={
            "Try asking the assistant to explain a concept, compare two topics, " +
            "or summarise a chapter from your uploaded documents."
          }
        />
      </div>
    );
  } else {
    content = (
      <ol className={styles.list} data-testid="chat-messages">
        {state.messages.map((msg) =>
          isAssistant(msg) ? (
            <AssistantMessage
              key={msg.id}
              message={msg}
              documentTitles={documentTitles}
            />
          ) : (
            <UserMessage key={msg.id} message={msg} />
          ),
        )}
        {pendingUserMessage ? (
          <li className={styles.pendingRow} data-testid="chat-pending-user">
            <UserMessage
              message={{
                id: "pending",
                session_id: "",
                role: "user",
                content: pendingUserMessage,
                created_at: new Date().toISOString(),
              }}
            />
            <div className={styles.pendingIndicator} role="status" aria-live="polite">
              <span className={styles.pendingDot} aria-hidden="true" />
              Generating response…
            </div>
          </li>
        ) : null}
      </ol>
    );
  }

  return (
    <div ref={scrollerRef} className={styles.scroller}>
      {content}
    </div>
  );
}
