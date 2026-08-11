"use client";

import { useEffect, useState } from "react";
import { chatApi } from "@/lib/api/chat";
import { EmptyState } from "@/components/primitives/EmptyState";
import { LoadingState } from "@/components/primitives/LoadingState";
import { APIError } from "@/types/api";
import styles from "./chat.module.css";

export function ChatPanel() {
  const [status, setStatus] = useState<"loading" | "ready" | "error">(
    "loading",
  );
  const [count, setCount] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const list = await chatApi.listSessions();
        if (!cancelled) {
          setCount(list.length);
          setStatus("ready");
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof APIError ? err.message : "Could not load conversations");
          setStatus("error");
        }
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className={styles.root}>
      <header className={styles.header}>
        <h1 className={styles.title}>Chat</h1>
        <p className={styles.subtitle}>
          Ask grounded questions against your document library.
        </p>
      </header>

      {status === "loading" && (
        <div className={styles.loading}>
          <LoadingState label="Loading conversations…" />
        </div>
      )}

      {status === "error" && (
        <EmptyState
          title="Could not load conversations"
          description={error ?? "Please try again in a moment."}
        />
      )}

      {status === "ready" && count === 0 && (
        <EmptyState
          title="No conversations yet"
          description="Start a conversation with your academic assistant."
        />
      )}

      {status === "ready" && count !== null && count > 0 && (
        <EmptyState
          title={`${count} conversation${count === 1 ? "" : "s"} saved`}
          description="The chat UI will land in a later phase. Your conversations are safely stored."
        />
      )}
    </div>
  );
}
