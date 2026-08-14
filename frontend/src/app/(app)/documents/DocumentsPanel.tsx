"use client";

import { useCallback, useEffect, useState } from "react";
import { documentsApi } from "@/lib/api/documents";
import { EmptyState } from "@/components/primitives/EmptyState";
import { ErrorState } from "@/components/primitives/ErrorState";
import { LoadingState } from "@/components/primitives/LoadingState";
import { Button } from "@/components/ui/Button";
import { DeleteConfirmDialog } from "./DeleteConfirmDialog";
import { DocumentList } from "./DocumentList";
import { DocumentUpload } from "./DocumentUpload";
import { ACCEPTED_FILE_EXTENSIONS, SUPPORTED_FORMATS_LABEL } from "@/lib/constants/upload";
import { APIError } from "@/types/api";
import type { Document } from "@/types";
import styles from "./documents.module.css";

type ListState =
  | { status: "loading" }
  | { status: "ready"; documents: Document[] }
  | { status: "error"; message: string };

/**
 * Documents page. Owns:
 *   - the GET /documents lifecycle (loading, ready, error, refresh)
 *   - the POST /documents/upload lifecycle (pending, error, success)
 *   - the DELETE /documents/{id} lifecycle (per-id pending, confirmation, error)
 *
 * Children components are pure: they never call the API on their own.
 */
export function DocumentsPanel() {
  const [list, setList] = useState<ListState>({ status: "loading" });
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState<Document | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setList({ status: "loading" });
    try {
      const items = await documentsApi.list();
      setList({ status: "ready", documents: items });
    } catch (err) {
      setList({
        status: "error",
        message: err instanceof APIError ? err.message : "Could not load documents",
      });
    }
  }, []);

  // One-shot initial load. The loading state is the default render
  // state, so we don't need to setState here — just dispatch the
  // network call and let the response handlers set the new state.
  // `refresh()` (which does flip to "loading") is reserved for the
  // user-driven refresh button so the panel can show a "Refreshing…"
  // affordance on subsequent clicks.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const items = await documentsApi.list();
        if (cancelled) return;
        setList({ status: "ready", documents: items });
      } catch (err) {
        if (cancelled) return;
        setList({
          status: "error",
          message:
            err instanceof APIError ? err.message : "Could not load documents",
        });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // -------- upload --------

  const handleUploadSelect = useCallback(
    async (file: File) => {
      setUploading(true);
      setUploadError(null);
      try {
        await documentsApi.upload(file);
        // Re-fetch the list so the new row appears with its real status.
        // We don't try to merge optimistically — the backend is the
        // source of truth and the upload endpoint returns the row
        // metadata, but listing ensures ordering + processing status
        // start where the backend actually has them.
        const items = await documentsApi.list();
        setList({ status: "ready", documents: items });
      } catch (err) {
        setUploadError(
          err instanceof APIError ? err.message : "Upload failed. Please try again.",
        );
      } finally {
        setUploading(false);
      }
    },
    [],
  );

  // -------- delete --------

  const handleRequestDelete = useCallback((document: Document) => {
    setDeleteError(null);
    setPendingDelete(document);
  }, []);

  const handleCancelDelete = useCallback(() => {
    if (deletingId) return;
    setPendingDelete(null);
    setDeleteError(null);
  }, [deletingId]);

  const handleConfirmDelete = useCallback(async () => {
    if (!pendingDelete) return;
    setDeletingId(pendingDelete.id);
    setDeleteError(null);
    try {
      await documentsApi.remove(pendingDelete.id);
      setPendingDelete(null);
      const items = await documentsApi.list();
      setList({ status: "ready", documents: items });
    } catch (err) {
      setDeleteError(
        err instanceof APIError ? err.message : "Delete failed. Please try again.",
      );
      // Keep the dialog open so the user can retry or cancel.
    } finally {
      setDeletingId(null);
    }
  }, [pendingDelete]);

  // -------- render --------

  const renderListContent = () => {
    if (list.status === "loading") {
      return (
        <div className={styles.loadingPanel} data-testid="documents-loading">
          <LoadingState label="Loading documents…" />
        </div>
      );
    }

    if (list.status === "error") {
      return (
        <ErrorState
          title="Could not load documents"
          description={list.message}
        />
      );
    }

    if (list.documents.length === 0) {
      return (
        <div data-testid="documents-empty-state">
          <EmptyState
            title="No documents yet"
            description={`Upload your first academic file to get started. Supported formats: ${SUPPORTED_FORMATS_LABEL}.`}
          />
        </div>
      );
    }

    return (
      <DocumentList
        documents={list.documents}
        deletingIds={new Set(deletingId ? [deletingId] : [])}
        onRequestDelete={handleRequestDelete}
      />
    );
  };

  const canRefresh = list.status !== "loading" && !uploading;

  return (
    <div className={styles.root}>
      <header className={styles.header}>
        <div className={styles.headerText}>
          <h1 className={styles.title}>Documents</h1>
          <p className={styles.subtitle}>Your academic knowledge base</p>
        </div>
        <Button
          type="button"
          variant="ghost"
          onClick={() => void refresh()}
          disabled={!canRefresh}
          data-testid="documents-refresh"
        >
          {list.status === "loading" ? "Refreshing…" : "Refresh"}
        </Button>
      </header>

      <section className={styles.uploadSection} aria-label="Upload document">
        <DocumentUpload
          onSelect={handleUploadSelect}
          pending={uploading}
          hint={
            uploadError
              ? uploadError
              : `Accepted file types: ${ACCEPTED_FILE_EXTENSIONS.join(", ")}.`
          }
        />
      </section>

      <section className={styles.listSection} aria-label="Your documents">
        {renderListContent()}
        {deleteError ? (
          <div className={styles.deleteError} role="alert" data-testid="documents-delete-error">
            {deleteError}
          </div>
        ) : null}
      </section>

      {pendingDelete ? (
        <DeleteConfirmDialog
          documentName={pendingDelete.original_filename}
          pending={deletingId !== null}
          onCancel={handleCancelDelete}
          onConfirm={() => void handleConfirmDelete()}
        />
      ) : null}
    </div>
  );
}