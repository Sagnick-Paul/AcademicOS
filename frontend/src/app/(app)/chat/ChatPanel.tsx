"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { chatApi } from "@/lib/api/chat";
import { documentsApi } from "@/lib/api/documents";
import { APIError } from "@/types/api";
import type {
  ChatMessage,
  ChatMessageWithSources,
  ChatSession,
  Document,
} from "@/types";

/**
 * Internal type used by the message list. The backend returns
 * user messages WITHOUT a `sources` field, so we widen the
 * stored type to `ChatMessage` and let the assistant branch
 * narrow to `ChatMessageWithSources` where it matters.
 */
type StoredMessage = ChatMessage | ChatMessageWithSources;
import { ChatMain } from "./components/ChatMain";
import { ChatSidebar } from "./components/ChatSidebar";
import styles from "./chat.module.css";

type SessionsState =
  | { status: "loading" }
  | { status: "ready"; sessions: readonly ChatSession[] }
  | { status: "error"; message: string };

type MessagesState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "ready"; messages: readonly StoredMessage[] }
  | { status: "error"; message: string };

const NO_DOCS: readonly Document[] = [];

/**
 * Chat experience orchestrator. Owns:
 *
 *   - the session list lifecycle (load, refresh on create/delete/send)
 *   - session selection
 *   - per-session message load
 *   - the send-message flow with an optimistic user bubble and
 *     a "Generating response…" indicator
 *   - the document-title map used to render source metadata
 *   - error surfaces for each of the three lifecycles
 *
 * Children are pure: they never call the API on their own.
 *
 * The backend is synchronous — `sendMessage` returns once the
 * assistant reply has been persisted, so we use an optimistic
 * user-message bubble that is replaced by the real pair from the
 * response. We do NOT fake streaming.
 */
export function ChatPanel() {
  const [sessionsState, setSessionsState] = useState<SessionsState>({
    status: "loading",
  });
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [messagesState, setMessagesState] = useState<MessagesState>({ status: "idle" });
  const [pendingUserMessage, setPendingUserMessage] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);
  const [creatingSession, setCreatingSession] = useState(false);
  const [documents, setDocuments] = useState<readonly Document[]>(NO_DOCS);
  // The composer text. We own it here so a failed send can restore
  // the user's draft instead of forcing them to retype.
  const [composerValue, setComposerValue] = useState("");

  // Track the active request token so a slow first request can't
  // overwrite a fresh one (e.g. user clicks session A, then session B
  // before A's response arrives).
  const loadTokenRef = useRef(0);

  // ---------- document title resolution ----------

  // We fetch the document list once (the user's library) and build a
  // map from document_id → original_filename. The session-messages
  // endpoint only returns document_id on each source, never the
  // title; without this map we'd be stuck rendering "Untitled".
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const docs = await documentsApi.list();
        if (!cancelled) setDocuments(docs);
      } catch {
        // Non-fatal: sources will fall back to "Untitled document".
        if (!cancelled) setDocuments(NO_DOCS);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const documentTitles = useMemo<ReadonlyMap<string, string>>(() => {
    const m = new Map<string, string>();
    for (const d of documents) m.set(d.id, d.original_filename);
    return m;
  }, [documents]);

  // ---------- sessions ----------

  const refreshSessions = useCallback(async () => {
    try {
      const list = await chatApi.listSessions();
      setSessionsState({ status: "ready", sessions: list });
      return list;
    } catch (err) {
      setSessionsState({
        status: "error",
        message:
          err instanceof APIError ? err.message : "Could not load conversations",
      });
      return null;
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const list = await chatApi.listSessions();
        if (cancelled) return;
        setSessionsState({ status: "ready", sessions: list });
        // If the URL is empty and we already have a session in storage,
        // we don't auto-select — the spec says user picks explicitly.
      } catch (err) {
        if (cancelled) return;
        setSessionsState({
          status: "error",
          message:
            err instanceof APIError
              ? err.message
              : "Could not load conversations",
        });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // ---------- message loading ----------

  const loadMessages = useCallback(async (sessionId: string) => {
    const token = ++loadTokenRef.current;
    setMessagesState({ status: "loading" });
    setSendError(null);
    try {
      const sess = await chatApi.getSession(sessionId);
      if (token !== loadTokenRef.current) return;
      setMessagesState({ status: "ready", messages: sess.messages });
    } catch (err) {
      if (token !== loadTokenRef.current) return;
      setMessagesState({
        status: "error",
        message:
          err instanceof APIError
            ? err.message
            : "Could not load messages",
      });
    }
  }, []);

  // ---------- session selection ----------

  const handleSelectSession = useCallback(
    (session: ChatSession) => {
      if (session.id === selectedSessionId) return;
      setSelectedSessionId(session.id);
      setPendingUserMessage(null);
      setSendError(null);
      void loadMessages(session.id);
    },
    [selectedSessionId, loadMessages],
  );

  // ---------- new session ----------

  const handleCreateSession = useCallback(async () => {
    if (creatingSession) return;
    setCreatingSession(true);
    setSendError(null);
    try {
      const created = await chatApi.createSession({});
      const list = await chatApi.listSessions();
      setSessionsState({ status: "ready", sessions: list });
      setSelectedSessionId(created.id);
      setMessagesState({ status: "ready", messages: [] });
    } catch (err) {
      // Surface the create failure inline near the sidebar button.
      setSendError(
        err instanceof APIError
          ? err.message
          : "Could not create a new conversation",
      );
    } finally {
      setCreatingSession(false);
    }
  }, [creatingSession]);

  // ---------- send ----------

  const handleSubmit = useCallback(
    async (text: string) => {
      if (!selectedSessionId || sending) return;
      setSending(true);
      setSendError(null);
      setPendingUserMessage(text);
      // Optimistically clear the composer; on error we restore the
      // draft so the user can retry without retyping.
      setComposerValue("");
      try {
        const result = await chatApi.sendMessage(selectedSessionId, {
          query: text,
        });
        // Replace the entire message list with the persisted pair
        // (user + assistant). Using the response directly is simpler
        // and authoritative — the backend has just committed them.
        // The user_message from the wire lacks `sources`, but our
        // StoredMessage union handles that.
        const next: StoredMessage[] = [result.user_message, result.assistant_message];
        setMessagesState({ status: "ready", messages: next });
        setPendingUserMessage(null);
        // Refresh the session list so updated_at + title reflect the
        // new activity (the title may have been derived from the
        // first message by the backend).
        void refreshSessions();
      } catch (err) {
        setPendingUserMessage(null);
        // Restore the user's draft so they can retry without
        // retyping. This is the production behavior of "the
        // composer remains usable".
        setComposerValue(text);
        setSendError(
          err instanceof APIError
            ? err.message
            : "Could not send the message. Please try again.",
        );
        // On a session-level error (404, 401, 503) the composer
        // remains usable so the user can retry or pick another
        // session.
      } finally {
        setSending(false);
      }
    },
    [selectedSessionId, sending, refreshSessions],
  );

  // ---------- render ----------

  // When no session is selected, the main area shows a friendly
  // "select or start" prompt instead of the composer.
  const selectedSession = useMemo<ChatSession | null>(() => {
    if (sessionsState.status !== "ready" || !selectedSessionId) return null;
    return (
      sessionsState.sessions.find((s) => s.id === selectedSessionId) ?? null
    );
  }, [sessionsState, selectedSessionId]);

  return (
    <div className={styles.root}>
      <header className={styles.header}>
        <div className={styles.headerText}>
          <h1 className={styles.title}>Chat</h1>
          <p className={styles.subtitle}>
            Ask grounded questions against your document library.
          </p>
        </div>
      </header>

      <div className={styles.workspace}>
        <ChatSidebar
          status={sessionsState.status === "loading" ? "loading" : sessionsState.status === "error" ? "error" : "ready"}
          error={sessionsState.status === "error" ? sessionsState.message : null}
          sessions={sessionsState.status === "ready" ? sessionsState.sessions : []}
          selectedSessionId={selectedSessionId}
          creating={creatingSession}
          onSelectSession={handleSelectSession}
          onCreateSession={() => void handleCreateSession()}
        />

        <ChatMain
          session={selectedSession}
          messages={
            messagesState.status === "idle"
              ? { status: "ready", messages: [] }
              : messagesState.status === "loading"
                ? { status: "loading" }
                : messagesState.status === "ready"
                  ? { status: "ready", messages: messagesState.messages }
                  : { status: "error", message: messagesState.message }
          }
          pendingUserMessage={pendingUserMessage}
          documentTitles={documentTitles}
          sending={sending}
          composerValue={composerValue}
          onComposerChange={setComposerValue}
          sendError={
            // Only show the composer-scoped error if the composer is
            // mounted (i.e. a session is selected). New-session
            // failures also land here but render below the workspace
            // so they're discoverable.
            selectedSession ? sendError : null
          }
          onSubmit={(text) => void handleSubmit(text)}
        />
      </div>

      {!selectedSession && sendError ? (
        <div
          className={styles.globalError}
          role="alert"
          data-testid="chat-global-error"
        >
          {sendError}
        </div>
      ) : null}
    </div>
  );
}
