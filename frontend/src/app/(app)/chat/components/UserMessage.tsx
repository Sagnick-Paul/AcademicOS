"use client";

import type { ChatMessage } from "@/types";
import styles from "./UserMessage.module.css";

interface UserMessageProps {
  message: ChatMessage;
}

/**
 * Single user message bubble. Pure presentational.
 *
 * We render `content` as preformatted text so the backend's
 * whitespace is preserved; the assistant message keeps the same
 * treatment to match.
 */
export function UserMessage({ message }: UserMessageProps) {
  return (
    <article
      className={styles.root}
      data-testid="chat-message-user"
      data-message-id={message.id}
    >
      <div className={styles.bubble}>{message.content}</div>
    </article>
  );
}
