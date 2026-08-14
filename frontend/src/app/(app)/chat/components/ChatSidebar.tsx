"use client";

import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/primitives/EmptyState";
import { ErrorState } from "@/components/primitives/ErrorState";
import { LoadingState } from "@/components/primitives/LoadingState";
import type { ChatSession } from "@/types";
import { SessionItem } from "./SessionItem";
import styles from "./ChatSidebar.module.css";

interface ChatSidebarProps {
  status: "loading" | "ready" | "error";
  error: string | null;
  sessions: readonly ChatSession[];
  selectedSessionId: string | null;
  creating: boolean;
  onSelectSession: (session: ChatSession) => void;
  onCreateSession: () => void;
}

/**
 * Left rail: "New chat" button + the user's session list.
 *
 * The parent owns every async lifecycle (loading state, list, error,
 * the create-session request, and selection). This component is
 * presentational and never calls the API itself.
 */
export function ChatSidebar({
  status,
  error,
  sessions,
  selectedSessionId,
  creating,
  onSelectSession,
  onCreateSession,
}: ChatSidebarProps) {
  return (
    <aside className={styles.sidebar} aria-label="Chat sessions">
      <div className={styles.header}>
        <h2 className={styles.title}>Conversations</h2>
        <Button
          type="button"
          variant="primary"
          fullWidth
          onClick={onCreateSession}
          disabled={creating}
          data-testid="chat-new-session"
        >
          {creating ? "Creating…" : "+ New chat"}
        </Button>
      </div>

      <div className={styles.body}>
        {status === "loading" ? (
          <div className={styles.loading} data-testid="chat-sessions-loading">
            <LoadingState label="Loading conversations…" />
          </div>
        ) : null}

        {status === "error" ? (
          <ErrorState
            title="Could not load conversations"
            description={error ?? "Please try again in a moment."}
          />
        ) : null}

        {status === "ready" && sessions.length === 0 ? (
          <div data-testid="chat-sessions-empty">
            <EmptyState
              title="No conversations yet"
              description="Start a new chat to ask a question about your library."
            />
          </div>
        ) : null}

        {status === "ready" && sessions.length > 0 ? (
          <ul className={styles.list} data-testid="chat-sessions-list">
            {sessions.map((session) => (
              <SessionItem
                key={session.id}
                session={session}
                selected={session.id === selectedSessionId}
                onSelect={onSelectSession}
              />
            ))}
          </ul>
        ) : null}
      </div>
    </aside>
  );
}
