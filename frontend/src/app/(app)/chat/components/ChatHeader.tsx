"use client";

import styles from "./ChatHeader.module.css";

interface ChatHeaderProps {
  title: string;
}

/**
 * Header for the main chat area. Renders the session title (or a
 * default when no session is selected). Pure presentational.
 */
export function ChatHeader({ title }: ChatHeaderProps) {
  return (
    <header className={styles.header} data-testid="chat-header">
      <h2 className={styles.title} title={title}>
        {title}
      </h2>
    </header>
  );
}
