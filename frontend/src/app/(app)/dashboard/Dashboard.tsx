"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/hooks/useAuth";
import { documentsApi } from "@/lib/api/documents";
import { chatApi } from "@/lib/api/chat";
import { EmptyState } from "@/components/primitives/EmptyState";
import { LoadingState } from "@/components/primitives/LoadingState";
import { APIError } from "@/types/api";
import styles from "./dashboard.module.css";

interface ResourceState<T> {
  status: "loading" | "ready" | "error";
  data: T | null;
  error: string | null;
}

const INITIAL_STATE: ResourceState<never> = {
  status: "loading",
  data: null,
  error: null,
};

/** Time-of-day greeting (kept simple — locale-aware math later if needed). */
function greetingFor(date: Date): string {
  const hour = date.getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

function safeError(err: unknown): string {
  if (err instanceof APIError) return err.message;
  if (err instanceof Error) return err.message;
  return "Something went wrong";
}

export function Dashboard() {
  const { user } = useAuth();
  const [documents, setDocuments] = useState<ResourceState<number>>(INITIAL_STATE);
  const [sessions, setSessions] = useState<ResourceState<number>>(INITIAL_STATE);

  // Fire both requests in parallel. Failures are isolated — one panel
  // can error without affecting the other.
  useEffect(() => {
    let cancelled = false;

    async function loadDocuments() {
      try {
        const list = await documentsApi.list();
        if (!cancelled) setDocuments({ status: "ready", data: list.length, error: null });
      } catch (err) {
        if (!cancelled)
          setDocuments({ status: "error", data: null, error: safeError(err) });
      }
    }

    async function loadSessions() {
      try {
        const list = await chatApi.listSessions();
        if (!cancelled) setSessions({ status: "ready", data: list.length, error: null });
      } catch (err) {
        if (!cancelled)
          setSessions({ status: "error", data: null, error: safeError(err) });
      }
    }

    void loadDocuments();
    void loadSessions();
    return () => {
      cancelled = true;
    };
  }, []);

  const greeting = greetingFor(new Date());
  const firstName = user?.full_name?.trim().split(/\s+/)[0] ?? "there";

  return (
    <div className={styles.root}>
      <header className={styles.header}>
        <h1 className={styles.greeting}>
          {greeting}, {firstName}
        </h1>
        <p className={styles.subtitle}>Your academic workspace</p>
      </header>

      <section className={styles.stats} aria-label="Workspace summary">
        <DocumentStatCard state={documents} />
        <ConversationStatCard state={sessions} />
      </section>

      <section className={styles.section} aria-labelledby="recent-activity">
        <h2 id="recent-activity" className={styles.sectionTitle}>
          Recent activity
        </h2>
        <RecentActivity documents={documents} sessions={sessions} />
      </section>

      <section className={styles.section} aria-labelledby="quick-actions">
        <h2 id="quick-actions" className={styles.sectionTitle}>
          Quick actions
        </h2>
        <div className={styles.quickActions}>
          <Link href="/documents" className={styles.quickAction}>
            <span className={styles.quickActionTitle}>Open Documents</span>
            <span className={styles.quickActionDescription}>
              Upload and manage academic material.
            </span>
          </Link>
          <Link href="/chat" className={styles.quickAction}>
            <span className={styles.quickActionTitle}>Start a Chat</span>
            <span className={styles.quickActionDescription}>
              Ask grounded questions against your library.
            </span>
          </Link>
        </div>
      </section>
    </div>
  );
}

// ---------- stat cards ----------

interface StatCardProps {
  label: string;
  state: ResourceState<number>;
  emptyLabel: string;
  loadingLabel: string;
}

function StatCard({ label, state, emptyLabel, loadingLabel }: StatCardProps) {
  return (
    <article className={styles.statCard} data-testid={`stat-${label.toLowerCase()}`}>
      <span className={styles.statLabel}>{label}</span>
      {state.status === "loading" && (
        <span className={styles.statCaption}>{loadingLabel}</span>
      )}
      {state.status === "ready" && (
        <span className={styles.statValue}>{state.data}</span>
      )}
      {state.status === "ready" && (
        <span className={styles.statCaption}>
          {state.data === 0 ? emptyLabel : ""}
        </span>
      )}
      {state.status === "error" && (
        <span className={styles.statError}>
          {state.error ?? "Could not load"}
        </span>
      )}
    </article>
  );
}

function DocumentStatCard({ state }: { state: ResourceState<number> }) {
  return (
    <StatCard
      label="Documents"
      state={state}
      emptyLabel="No documents yet"
      loadingLabel="Loading…"
    />
  );
}

function ConversationStatCard({ state }: { state: ResourceState<number> }) {
  return (
    <StatCard
      label="Conversations"
      state={state}
      emptyLabel="No conversations yet"
      loadingLabel="Loading…"
    />
  );
}

// ---------- recent activity ----------

interface RecentActivityProps {
  documents: ResourceState<number>;
  sessions: ResourceState<number>;
}

function RecentActivity({ documents, sessions }: RecentActivityProps) {
  // Show a loading panel only if both are still loading.
  const allLoading =
    documents.status === "loading" && sessions.status === "loading";
  if (allLoading) {
    return (
      <div className={styles.loadingPanel}>
        <LoadingState label="Loading activity…" />
      </div>
    );
  }

  // If we have at least one count > 0, surface it. Otherwise, an empty state.
  const hasAny =
    (documents.status === "ready" && documents.data && documents.data > 0) ||
    (sessions.status === "ready" && sessions.data && sessions.data > 0);

  if (hasAny) {
    return (
      <EmptyState
        title="You're getting started"
        description="Recent uploads and conversations will appear here as you use AcademicOS."
      />
    );
  }

  return (
    <EmptyState
      title="No recent activity yet"
      description="Upload your first document or start a chat conversation to see activity here."
    />
  );
}
