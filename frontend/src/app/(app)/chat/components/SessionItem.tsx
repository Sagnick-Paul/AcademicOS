"use client";

import { cn } from "@/lib/utils/cn";
import { formatDate } from "@/lib/utils/format";
import type { ChatSession } from "@/types";
import styles from "./SessionItem.module.css";

interface SessionItemProps {
  session: ChatSession;
  selected: boolean;
  onSelect: (session: ChatSession) => void;
}

/**
 * Single session row in the chat sidebar. Pure presentational: the
 * parent owns the selection state and the click handler.
 *
 * The backend always returns a real `title` (it defaults to "New chat"
 * and can be derived from `initial_query` on creation). We display
 * `title`; if the user has never sent a message, we use the created
 * date as a sub-label.
 */
export function SessionItem({ session, selected, onSelect }: SessionItemProps) {
  const handleClick = () => onSelect(session);

  return (
    <li className={styles.item}>
      <button
        type="button"
        className={cn(styles.button, selected && styles.buttonSelected)}
        onClick={handleClick}
        aria-current={selected ? "true" : "false"}
        data-testid="chat-session-item"
        data-session-id={session.id}
      >
        <span className={styles.title} title={session.title}>
          {session.title}
        </span>
        <span className={styles.meta}>
          {formatDate(session.updated_at)}
        </span>
      </button>
    </li>
  );
}
