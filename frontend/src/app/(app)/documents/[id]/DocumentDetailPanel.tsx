"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { documentsApi } from "@/lib/api/documents";
import { coursesApi } from "@/lib/api/courses";
import { chatApi } from "@/lib/api/chat";
import { ErrorState } from "@/components/primitives/ErrorState";
import { LoadingState } from "@/components/primitives/LoadingState";
import { Button } from "@/components/ui/Button";
import { DocumentEditDialog } from "../DocumentEditDialog";
import { DeleteConfirmDialog } from "../DeleteConfirmDialog";
import { formatDate, formatFileSize } from "@/lib/utils/format";
import { DOCUMENT_TYPE_LABELS } from "@/types";
import { APIError } from "@/types/api";
import type { Course, Document, DocumentUpdate } from "@/types";
import styles from "./DocumentDetailPanel.module.css";

interface DocumentDetailPanelProps {
  documentId: string;
}

type DetailState =
  | { status: "loading" }
  | { status: "ready"; document: Document }
  | { status: "error"; message: string; notFound?: boolean };

export function DocumentDetailPanel({ documentId }: DocumentDetailPanelProps) {
  const router = useRouter();
  
  const [state, setState] = useState<DetailState>({ status: "loading" });
  const [courses, setCourses] = useState<Course[]>([]);
  
  // Dialog states
  const [isEditing, setIsEditing] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  // In-flight operation states
  const [isUpdating, setIsUpdating] = useState(false);
  const [updateError, setUpdateError] = useState<string | null>(null);

  const [isConfirmingDelete, setIsConfirmingDelete] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const [isCreatingChat, setIsCreatingChat] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const doc = await documentsApi.get(documentId);
        if (cancelled) return;
        setState({ status: "ready", document: doc });
      } catch (err) {
        if (cancelled) return;
        if (err instanceof APIError && err.status === 404) {
          setState({ status: "error", message: "Document not found.", notFound: true });
        } else {
          setState({
            status: "error",
            message: err instanceof APIError ? err.message : "Failed to load document.",
          });
        }
      }
    })();

    (async () => {
      try {
        const res = await coursesApi.list();
        if (cancelled) return;
        setCourses(res.items);
      } catch (err) {
        console.error("Failed to load courses", err);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [documentId]);

  const handleUpdate = useCallback(
    async (payload: DocumentUpdate) => {
      setIsUpdating(true);
      setUpdateError(null);
      try {
        const updatedDoc = await documentsApi.update(documentId, payload);
        setState({ status: "ready", document: updatedDoc });
        setIsEditing(false);
      } catch (err) {
        setUpdateError(
          err instanceof APIError ? err.message : "Update failed. Please try again."
        );
      } finally {
        setIsUpdating(false);
      }
    },
    [documentId]
  );

  const handleDelete = useCallback(async () => {
    setIsConfirmingDelete(true);
    setDeleteError(null);
    try {
      await documentsApi.remove(documentId);
      setIsDeleting(false);
      router.push("/documents");
    } catch (err) {
      setDeleteError(
        err instanceof APIError ? err.message : "Failed to delete document. Please try again."
      );
      setIsConfirmingDelete(false);
    }
  }, [documentId, router]);

  const handleViewDocument = useCallback(() => {
    // The content endpoint returns a FileResponse, which the browser
    // can render natively (PDF) or download (PPTX).
    const url = `/api/v1/documents/${documentId}/content`;
    window.open(url, "_blank");
  }, [documentId]);

  const handleChatWithDocument = useCallback(async () => {
    setIsCreatingChat(true);
    setChatError(null);
    try {
      const session = await chatApi.createSession({
        document_id: documentId,
        title: `Chat with ${state.status === "ready" ? state.document.original_filename : "document"}`,
      });
      router.push(`/chat/${session.id}`);
    } catch (err) {
      setChatError(
        err instanceof APIError ? err.message : "Failed to create chat session. Please try again."
      );
    } finally {
      setIsCreatingChat(false);
    }
  }, [documentId, router, state]);

  if (state.status === "loading") {
    return (
      <div className={styles.loadingPanel} data-testid="document-detail-loading">
        <LoadingState label="Loading document…" />
      </div>
    );
  }

  if (state.status === "error") {
    return (
      <div className={styles.root} data-testid="document-detail-error">
        <Link href="/documents" className={styles.backLink}>
          ← Back to Documents
        </Link>
        <ErrorState 
          title={state.notFound ? "Document Not Found" : "Error Loading Document"} 
          description={state.message} 
        />
      </div>
    );
  }

  const { document } = state;
  const course = courses.find((c) => c.id === document.course_id);
  const metadata = document.document_metadata;

  return (
    <div className={styles.root} data-testid="document-detail-ready">
      <Link href="/documents" className={styles.backLink}>
        ← Back to Documents
      </Link>

      <header className={styles.header}>
        <h1 className={styles.title}>{document.filename}</h1>
        <p className={styles.subtitle}>
          {document.document_type ? DOCUMENT_TYPE_LABELS[document.document_type] : "Untyped"}
          {" · "}
          {course ? (course.code ? `${course.code} — ${course.name}` : course.name) : "Unassigned"}
        </p>
      </header>

      <div className={styles.content}>
        <section className={styles.section} aria-label="Document Information">
          <h2 className={styles.sectionTitle}>Document Information</h2>
          <div className={styles.grid}>
            <div className={styles.field}>
              <span className={styles.label}>Course</span>
              {course ? (
                <span className={styles.value}>{course.name}</span>
              ) : (
                <span className={styles.valueEmpty}>Unassigned</span>
              )}
            </div>
            
            <div className={styles.field}>
              <span className={styles.label}>Document Type</span>
              {document.document_type ? (
                <span className={styles.value}>{DOCUMENT_TYPE_LABELS[document.document_type]}</span>
              ) : (
                <span className={styles.valueEmpty}>Untyped</span>
              )}
            </div>

            <div className={styles.field}>
              <span className={styles.label}>Processing Status</span>
              <span className={styles.value} style={{ textTransform: "capitalize" }}>
                {document.upload_status}
              </span>
            </div>

            <div className={styles.field}>
              <span className={styles.label}>Original Filename</span>
              <span className={styles.value}>{document.original_filename}</span>
            </div>
            
            <div className={styles.field}>
              <span className={styles.label}>Created</span>
              <span className={styles.value}>
                {new Date(document.created_at).toLocaleString()}
              </span>
            </div>
            
            <div className={styles.field}>
              <span className={styles.label}>Last Updated</span>
              <span className={styles.value}>
                {new Date(document.updated_at).toLocaleString()}
              </span>
            </div>
          </div>
        </section>

        <section className={styles.section} aria-label="Metadata">
          <h2 className={styles.sectionTitle}>Metadata</h2>
          <div className={styles.grid}>
            <div className={styles.field}>
              <span className={styles.label}>Author</span>
              {metadata?.author ? (
                <span className={styles.value}>{metadata.author}</span>
              ) : (
                <span className={styles.valueEmpty}>Not specified</span>
              )}
            </div>

            <div className={styles.field}>
              <span className={styles.label}>Subject</span>
              {metadata?.subject ? (
                <span className={styles.value}>{metadata.subject}</span>
              ) : (
                <span className={styles.valueEmpty}>Not specified</span>
              )}
            </div>

            <div className={styles.field}>
              <span className={styles.label}>Semester</span>
              {metadata?.semester ? (
                <span className={styles.value}>{metadata.semester}</span>
              ) : (
                <span className={styles.valueEmpty}>Not specified</span>
              )}
            </div>

            <div className={styles.field}>
              <span className={styles.label}>Academic Year</span>
              {metadata?.academic_year ? (
                <span className={styles.value}>{metadata.academic_year}</span>
              ) : (
                <span className={styles.valueEmpty}>Not specified</span>
              )}
            </div>
          </div>
          
          <div className={styles.field} style={{ marginTop: "var(--space-2)" }}>
            <span className={styles.label}>Tags</span>
            {metadata?.tags && metadata.tags.length > 0 ? (
              <ul className={styles.tagsList}>
                {metadata.tags.map(tag => (
                  <li key={tag} className={styles.tag}>{tag}</li>
                ))}
              </ul>
            ) : (
              <span className={styles.valueEmpty}>No tags</span>
            )}
          </div>
        </section>

        <div className={styles.actions}>
          <Button
            variant="primary"
            onClick={handleViewDocument}
          >
            View Document
          </Button>
          <Button
            variant="secondary"
            onClick={handleChatWithDocument}
            disabled={isCreatingChat}
          >
            {isCreatingChat ? "Creating chat…" : "Chat with this Document"}
          </Button>
          <Button variant="primary" onClick={() => setIsEditing(true)}>
            Edit Document
          </Button>
          <Button variant="danger" onClick={() => setIsDeleting(true)}>
            Delete Document
          </Button>
          {chatError && <p className={styles.actionError}>{chatError}</p>}
        </div>
      </div>

      {isEditing && (
        <DocumentEditDialog
          document={document}
          courses={courses}
          pending={isUpdating}
          error={updateError}
          onConfirm={handleUpdate}
          onCancel={() => {
            setIsEditing(false);
            setUpdateError(null);
          }}
        />
      )}

      {isDeleting && (
        <DeleteConfirmDialog
          documentName={document.filename}
          pending={isConfirmingDelete}
          error={deleteError}
          onConfirm={handleDelete}
          onCancel={() => {
            setIsDeleting(false);
            setDeleteError(null);
          }}
        />
      )}
    </div>
  );
}
