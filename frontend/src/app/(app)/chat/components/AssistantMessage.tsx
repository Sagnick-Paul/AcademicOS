"use client";

import type { ChatMessageSource, ChatMessageWithSources } from "@/types";
import { SourceList } from "./SourceList";
import styles from "./AssistantMessage.module.css";

interface AssistantMessageProps {
  message: ChatMessageWithSources;
  /**
   * Map of document_id → user's filename. Used to render the
   * human-readable document title next to each source. If a
   * document is missing from the map, the source falls back to
   * "Untitled document" — we never invent a name.
   */
  documentTitles: ReadonlyMap<string, string>;
}

/**
 * Single assistant message: the answer text + the collapsible
 * SourceList. Pure presentational. Renders the assistant's reply
 * as preformatted text so the backend's whitespace is preserved.
 */
export function AssistantMessage({ message, documentTitles }: AssistantMessageProps) {
  return (
    <article
      className={styles.root}
      data-testid="chat-message-assistant"
      data-message-id={message.id}
    >
      <div className={styles.bubble}>
        <div className={styles.content}>{message.content}</div>
        <SourceList
          sources={message.sources as readonly ChatMessageSource[]}
          documentTitles={documentTitles}
        />
      </div>
    </article>
  );
}
