"use client";

import { EmptyState } from "@/components/primitives/EmptyState";
import type { ChatMessage, ChatMessageWithSources, ChatSession } from "@/types";
import { ChatHeader } from "./ChatHeader";
import { MessageComposer } from "./MessageComposer";
import { MessageList } from "./MessageList";
import styles from "./ChatMain.module.css";

type StoredMessage = ChatMessage | ChatMessageWithSources;

type LoadState =
  | { status: "loading" }
  | { status: "ready"; messages: readonly StoredMessage[] }
  | { status: "error"; message: string };

interface ChatMainProps {
  session: ChatSession | null;
  messages: LoadState;
  pendingUserMessage: string | null;
  documentTitles: ReadonlyMap<string, string>;
  sending: boolean;
  sendError: string | null;
  composerValue: string;
  onComposerChange: (next: string) => void;
  onSubmit: (text: string) => void;
}

/**
 * The right-hand panel of the chat page: header + message list +
 * composer. Owns no state of its own; the parent (ChatPanel) wires
 * everything together.
 */
export function ChatMain({
  session,
  messages,
  pendingUserMessage,
  documentTitles,
  sending,
  sendError,
  composerValue,
  onComposerChange,
  onSubmit,
}: ChatMainProps) {
  return (
    <section className={styles.root} aria-label="Chat conversation">
      <ChatHeader title={session?.title ?? "AcademicOS Chat"} />

      {session ? (
        <MessageList
          state={messages}
          pendingUserMessage={pendingUserMessage}
          documentTitles={documentTitles}
        />
      ) : (
        <div className={styles.empty} data-testid="chat-no-session">
          <EmptyState
            title="Select or start a conversation"
            description="Choose a conversation from the sidebar, or click '+ New chat' to begin."
          />
        </div>
      )}

      {session ? (
        <MessageComposer
          pending={sending}
          error={sendError}
          value={composerValue}
          onChange={onComposerChange}
          onSubmit={onSubmit}
        />
      ) : null}
    </section>
  );
}
