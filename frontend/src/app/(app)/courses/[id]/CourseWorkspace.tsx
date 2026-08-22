"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { coursesApi } from "@/lib/api/courses";
import { documentsApi } from "@/lib/api/documents";
import { chatApi } from "@/lib/api/chat";
import { EmptyState } from "@/components/primitives/EmptyState";
import { ErrorState } from "@/components/primitives/ErrorState";
import { LoadingState } from "@/components/primitives/LoadingState";
import { Button } from "@/components/ui/Button";
import { DocumentList } from "../../documents/DocumentList";
import { CourseDeleteDialog } from "../CourseDeleteDialog";
import { CourseForm } from "../CourseForm";
import { formatDate } from "@/lib/utils/format";
import { APIError } from "@/types/api";
import type {
  ChatSession,
  Course,
  CourseUpdate,
  Document,
  UUID,
} from "@/types";
import styles from "../courses.module.css";

type CourseState =
  | { status: "loading" }
  | { status: "ready"; course: Course }
  | { status: "error"; message: string };

type DocumentsState =
  | { status: "loading" }
  | { status: "ready"; documents: Document[] }
  | { status: "error"; message: string };

type SessionsState =
  | { status: "loading" }
  | { status: "ready"; sessions: ChatSession[] }
  | { status: "error"; message: string };

interface CourseWorkspaceProps {
  courseId: UUID;
}

/**
 * /courses/{id} — course detail + the documents and chat sessions
 * linked to it. Owns every async lifecycle; child components are pure.
 *
 * The chat session listing here is read-only: we link to /chat so the
 * user can continue the conversation there. We deliberately do NOT
 * redesign the chat experience in Phase 6D.
 */
export function CourseWorkspace({ courseId }: CourseWorkspaceProps) {
  const router = useRouter();
  const [courseState, setCourseState] = useState<CourseState>({ status: "loading" });
  const [documentsState, setDocumentsState] = useState<DocumentsState>({ status: "loading" });
  const [sessionsState, setSessionsState] = useState<SessionsState>({ status: "loading" });

  const [editing, setEditing] = useState(false);
  const [updatePending, setUpdatePending] = useState(false);
  const [updateError, setUpdateError] = useState<string | null>(null);

  const [pendingDelete, setPendingDelete] = useState(false);
  const [deletePending, setDeletePending] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  // ---------- loaders ----------

  const loadCourse = useCallback(async () => {
    setCourseState({ status: "loading" });
    try {
      const course = await coursesApi.get(courseId);
      setCourseState({ status: "ready", course });
    } catch (err) {
      setCourseState({
        status: "error",
        message:
          err instanceof APIError ? err.message : "Could not load course",
      });
    }
  }, [courseId]);

  const loadDocuments = useCallback(async () => {
    setDocumentsState({ status: "loading" });
    try {
      const docs = await documentsApi.list({ course_id: courseId });
      setDocumentsState({ status: "ready", documents: docs });
    } catch (err) {
      setDocumentsState({
        status: "error",
        message:
          err instanceof APIError
            ? err.message
            : "Could not load documents",
      });
    }
  }, [courseId]);

  const loadSessions = useCallback(async () => {
    setSessionsState({ status: "loading" });
    try {
      const sessions = await chatApi.listSessions({ course_id: courseId });
      setSessionsState({ status: "ready", sessions });
    } catch (err) {
      setSessionsState({
        status: "error",
        message:
          err instanceof APIError
            ? err.message
            : "Could not load conversations",
      });
    }
  }, [courseId]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      await Promise.all([
        loadCourse(),
        loadDocuments(),
        loadSessions(),
      ]);
      if (cancelled) return;
      void cancelled;
    })();
    return () => {
      cancelled = true;
    };
  }, [loadCourse, loadDocuments, loadSessions]);

  // ---------- update ----------

  const handleUpdate = useCallback(
    async (payload: CourseUpdate) => {
      setUpdatePending(true);
      setUpdateError(null);
      try {
        await coursesApi.update(courseId, payload);
        await loadCourse();
        setEditing(false);
      } catch (err) {
        setUpdateError(
          err instanceof APIError
            ? err.message
            : "Could not update the course. Please try again.",
        );
      } finally {
        setUpdatePending(false);
      }
    },
    [courseId, loadCourse],
  );

  // ---------- delete ----------

  const handleRequestDelete = useCallback(() => {
    setDeleteError(null);
    setPendingDelete(true);
  }, []);

  const handleCancelDelete = useCallback(() => {
    if (deletePending) return;
    setPendingDelete(false);
    setDeleteError(null);
  }, [deletePending]);

  // Note: actual deletion is wired up via the workspace's delete
  // confirmation dialog. The redirect to /courses after deletion is
  // handled by the router; we don't navigate inside this effect.
  void handleRequestDelete;

  // ---------- render ----------

  if (courseState.status === "loading") {
    return (
      <div className={styles.root}>
        <LoadingState label="Loading course…" />
      </div>
    );
  }

  if (courseState.status === "error") {
    return (
      <ErrorState
        title="Could not load course"
        description={courseState.message}
      />
    );
  }

  const course = courseState.course;

  return (
    <div className={styles.root}>
      <header className={styles.workspaceHeader}>
        <div className={styles.workspaceBreadcrumb}>
          <Link
            href="/courses"
            className={styles.workspaceBreadcrumbLink}
            data-testid="course-workspace-back"
          >
            ← Courses
          </Link>
        </div>
        <div className={styles.header}>
          <div className={styles.headerText}>
            <h1 className={styles.title} data-testid="course-workspace-title">
              {course.name}
            </h1>
            {course.code ? (
              <p className={styles.cardCode} data-testid="course-workspace-code">
                {course.code}
              </p>
            ) : null}
          </div>
          <div className={styles.workspaceActions}>
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                setEditing((current) => !current);
                setUpdateError(null);
              }}
              data-testid="course-workspace-edit"
            >
              {editing ? "Close" : "Edit"}
            </Button>
            <Button
              type="button"
              variant="danger"
              onClick={handleRequestDelete}
              data-testid="course-workspace-delete"
            >
              Delete
            </Button>
          </div>
        </div>
      </header>

      {editing ? (
        <section className={styles.createSection} aria-label="Edit course">
          <CourseForm
            key={course.id}
            course={course}
            pending={updatePending}
            errorMessage={updateError}
            onSubmit={(payload) => void handleUpdate(payload)}
            onCancel={() => {
              setEditing(false);
              setUpdateError(null);
            }}
            submitLabel="Save changes"
          />
        </section>
      ) : null}

      <section
        className={styles.workspaceSummary}
        aria-label="Course summary"
        data-testid="course-workspace-summary"
      >
        <div>
          <span className={styles.workspaceSummaryLabel}>Created</span>
          {formatDate(course.created_at)}
        </div>
        <div>
          <span className={styles.workspaceSummaryLabel}>Updated</span>
          {formatDate(course.updated_at)}
        </div>
        {course.description ? (
          <div>
            <span className={styles.workspaceSummaryLabel}>Description</span>
            {course.description}
          </div>
        ) : null}
      </section>

      <section className={styles.workspaceDocumentsSection} aria-label="Course documents">
        <div className={styles.header}>
          <h2 className={styles.workspaceSectionTitle}>Documents</h2>
          <div className={styles.headerActions}>
            <Button
              type="button"
              variant="ghost"
              onClick={() => void loadDocuments()}
              disabled={documentsState.status === "loading"}
              data-testid="course-workspace-refresh-documents"
            >
              {documentsState.status === "loading" ? "Refreshing…" : "Refresh"}
            </Button>
            <Link
              href={`/documents?course_id=${courseId}`}
              className={styles.workspaceBreadcrumbLink}
              data-testid="course-workspace-open-documents"
            >
              View all documents
            </Link>
          </div>
        </div>

        {documentsState.status === "loading" ? (
          <LoadingState label="Loading documents…" />
        ) : null}

        {documentsState.status === "error" ? (
          <ErrorState
            title="Could not load documents"
            description={documentsState.message}
          />
        ) : null}

        {documentsState.status === "ready" && documentsState.documents.length === 0 ? (
          <div data-testid="course-workspace-documents-empty">
            <EmptyState
              title="No documents in this course"
              description="Upload a document and assign it to this course to see it here."
            />
          </div>
        ) : null}

        {documentsState.status === "ready" && documentsState.documents.length > 0 ? (
          <DocumentList
            documents={documentsState.documents}
            deletingIds={new Set()}
            onRequestDelete={() => undefined}
            onRequestEdit={() => undefined}
          />
        ) : null}
      </section>

      <section className={styles.workspaceDocumentsSection} aria-label="Course conversations">
        <div className={styles.header}>
          <h2 className={styles.workspaceSectionTitle}>Conversations</h2>
        </div>

        {sessionsState.status === "loading" ? (
          <LoadingState label="Loading conversations…" />
        ) : null}

        {sessionsState.status === "error" ? (
          <ErrorState
            title="Could not load conversations"
            description={sessionsState.message}
          />
        ) : null}

        {sessionsState.status === "ready" && sessionsState.sessions.length === 0 ? (
          <div data-testid="course-workspace-sessions-empty">
            <EmptyState
              title="No conversations yet"
              description="Start a chat and link it to this course to see it here."
            />
          </div>
        ) : null}

        {sessionsState.status === "ready" && sessionsState.sessions.length > 0 ? (
          <ul
            className={styles.list}
            aria-label="Course conversations"
            data-testid="course-workspace-sessions-list"
          >
            {sessionsState.sessions.map((session) => (
              <li key={session.id} className={styles.listItem}>
                <article className={styles.card} data-testid="course-workspace-session">
                  <header className={styles.cardHeader}>
                    <div className={styles.cardTitleRow}>
                      <span className={styles.cardTitle}>{session.title}</span>
                      <span className={styles.cardMeta}>
                        Updated {formatDate(session.updated_at)}
                      </span>
                    </div>
                  </header>
                  <footer className={styles.cardActions}>
                    <Link
                      href="/chat"
                      className={styles.workspaceBreadcrumbLink}
                      data-testid="course-workspace-open-chat"
                    >
                      Open in chat
                    </Link>
                  </footer>
                </article>
              </li>
            ))}
          </ul>
        ) : null}
      </section>

      {pendingDelete ? (
        <CourseDeleteDialog
          courseName={course.name}
          pending={deletePending}
          onCancel={handleCancelDelete}
          onConfirm={() => {
            setDeletePending(true);
            setDeleteError(null);
            void coursesApi
              .remove(courseId)
              .then(() => {
                router.push("/courses");
              })
              .catch((err: unknown) => {
                setDeleteError(
                  err instanceof APIError
                    ? err.message
                    : "Delete failed. Please try again.",
                );
              })
              .finally(() => {
                setDeletePending(false);
              });
          }}
        />
      ) : null}

      {deleteError ? (
        <div className={styles.deleteError} role="alert" data-testid="course-workspace-delete-error">
          {deleteError}
        </div>
      ) : null}
    </div>
  );
}
