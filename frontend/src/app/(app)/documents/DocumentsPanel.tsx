"use client";

import { useEffect, useState } from "react";
import { documentsApi } from "@/lib/api/documents";
import { EmptyState } from "@/components/primitives/EmptyState";
import { LoadingState } from "@/components/primitives/LoadingState";
import { APIError } from "@/types/api";
import styles from "./documents.module.css";

export function DocumentsPanel() {
  const [status, setStatus] = useState<"loading" | "ready" | "error">(
    "loading",
  );
  const [count, setCount] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const list = await documentsApi.list();
        if (!cancelled) {
          setCount(list.length);
          setStatus("ready");
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof APIError ? err.message : "Could not load documents");
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
        <h1 className={styles.title}>Documents</h1>
        <p className={styles.subtitle}>
          Uploaded academic material appears here.
        </p>
      </header>

      {status === "loading" && (
        <div className={styles.loading}>
          <LoadingState label="Loading documents…" />
        </div>
      )}

      {status === "error" && (
        <EmptyState
          title="Could not load documents"
          description={error ?? "Please try again in a moment."}
        />
      )}

      {status === "ready" && count === 0 && (
        <EmptyState
          title="No documents yet"
          description="Your uploaded academic material will appear here."
        />
      )}

      {status === "ready" && count !== null && count > 0 && (
        <EmptyState
          title={`${count} document${count === 1 ? "" : "s"} ready`}
          description="The document library UI will land in a later phase. Your documents are safely stored."
        />
      )}
    </div>
  );
}
