"use client";

import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import { documentsApi } from "@/lib/api/documents";
import { coursesApi } from "@/lib/api/courses";
import { EmptyState } from "@/components/primitives/EmptyState";
import { ErrorState } from "@/components/primitives/ErrorState";
import { LoadingState } from "@/components/primitives/LoadingState";
import { Button } from "@/components/ui/Button";
import { DeleteConfirmDialog } from "./DeleteConfirmDialog";
import { DocumentList } from "./DocumentList";
import { DocumentUpload } from "./DocumentUpload";
import { DocumentEditDialog } from "./DocumentEditDialog";
import { DocumentUploadDetailsDialog } from "./DocumentUploadDetailsDialog";
import { ACCEPTED_FILE_EXTENSIONS, SUPPORTED_FORMATS_LABEL } from "@/lib/constants/upload";
import { DOCUMENT_TYPE_LABELS, DOCUMENT_TYPE_VALUES } from "@/types";
import { APIError } from "@/types/api";
import type { Course, Document, DocumentType, DocumentUpdate, DocumentUploadOptions } from "@/types";
import styles from "./documents.module.css";

type ListState =
  | { status: "loading" }
  | { status: "ready"; documents: Document[] }
  | { status: "error"; message: string };

type CoursesState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "ready"; courses: Course[] }
  | { status: "error"; message: string };

interface Filters {
  course_id: string | null;
  document_type: DocumentType;
}

/**
 * Documents page. Owns:
 *   - the GET /documents lifecycle (loading, ready, error, refresh)
 *   - the POST /documents/upload lifecycle (pending, error, success)
 *   - the DELETE /documents/{id} lifecycle (per-id pending, confirmation, error)
 *   - Phase 6B/6C/6D: course and document-type filters via URL query params
 *
 * Children components are pure: they never call the API on their own.
 */
export function DocumentsPanel() {
  // `useSearchParams` requires a Suspense boundary in the App Router.
  // Splitting root vs. inner keeps the boundary at the page level
  // without polluting the API surface.
  return (
    <Suspense fallback={<DocumentsPanelLoading />}>
      <DocumentsPanelInner />
    </Suspense>
  );
}

function DocumentsPanelLoading() {
  return (
    <div className={styles.root}>
      <div className={styles.loadingPanel} data-testid="documents-loading">
        <LoadingState label="Loading documents…" />
      </div>
    </div>
  );
}

function DocumentsPanelInner() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const [list, setList] = useState<ListState>({ status: "loading" });
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [pendingUploadFile, setPendingUploadFile] = useState<File | null>(null);
  const [pendingDelete, setPendingDelete] = useState<Document | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [pendingEditDocument, setPendingEditDocument] = useState<Document | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [updateError, setUpdateError] = useState<string | null>(null);
  const [coursesState, setCoursesState] = useState<CoursesState>({ status: "idle" });

  // ---------- URL-driven filters ----------

  const filters: Filters = useMemo(() => {
    const courseParam = searchParams.get("course_id");
    const typeParam = searchParams.get("document_type");
    const validType = DOCUMENT_TYPE_VALUES.find((value) => value === typeParam);
    return {
      course_id: courseParam,
      document_type: validType ?? null,
    };
  }, [searchParams]);

  const filtersActive = filters.course_id !== null || filters.document_type !== null;

  const writeFilters = useCallback(
    (next: Filters) => {
      const params = new URLSearchParams();
      if (next.course_id) params.set("course_id", next.course_id);
      if (next.document_type) params.set("document_type", next.document_type);
      const qs = params.toString();
      router.replace(qs ? `${pathname}?${qs}` : pathname);
    },
    [pathname, router],
  );

  const handleCourseFilterChange = useCallback(
    (event: React.ChangeEvent<HTMLSelectElement>) => {
      const value = event.target.value;
      writeFilters({
        course_id: value === "" ? null : value,
        document_type: filters.document_type,
      });
    },
    [filters.document_type, writeFilters],
  );

  const handleTypeFilterChange = useCallback(
    (event: React.ChangeEvent<HTMLSelectElement>) => {
      const value = event.target.value;
      const next = DOCUMENT_TYPE_VALUES.find((candidate) => candidate === value) ?? null;
      writeFilters({
        course_id: filters.course_id,
        document_type: next,
      });
    },
    [filters.course_id, writeFilters],
  );

  const handleClearFilters = useCallback(() => {
    writeFilters({ course_id: null, document_type: null });
  }, [writeFilters]);

  // ---------- list load ----------

  const listParams = useMemo(() => {
    const out: { course_id?: string; document_type?: DocumentType } = {};
    if (filters.course_id) out.course_id = filters.course_id;
    if (filters.document_type) out.document_type = filters.document_type;
    return out;
  }, [filters.course_id, filters.document_type]);

  const refresh = useCallback(async () => {
    setList({ status: "loading" });
    try {
      const items = await documentsApi.list(listParams);
      setList({ status: "ready", documents: items });
    } catch (err) {
      setList({
        status: "error",
        message: err instanceof APIError ? err.message : "Could not load documents",
      });
    }
  }, [listParams]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const items = await documentsApi.list(listParams);
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
  }, [listParams]);

  // ---------- courses load (for the course filter dropdown) ----------

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setCoursesState({ status: "loading" });
      try {
        const response = await coursesApi.list();
        if (cancelled) return;
        setCoursesState({ status: "ready", courses: response.items });
      } catch (err) {
        if (cancelled) return;
        setCoursesState({
          status: "error",
          message:
            err instanceof APIError ? err.message : "Could not load courses",
        });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // -------- upload --------

  const handleUploadSelect = useCallback(
    (file: File) => {
      setPendingUploadFile(file);
      setUploadError(null);
    },
    [],
  );

  const handleUploadConfirm = useCallback(
    async (options: DocumentUploadOptions) => {
      if (!pendingUploadFile) return;
      setUploading(true);
      setUploadError(null);
      try {
        await documentsApi.upload(pendingUploadFile, options);
        setPendingUploadFile(null);
        const items = await documentsApi.list(listParams);
        setList({ status: "ready", documents: items });
      } catch (err) {
        setUploadError(
          err instanceof APIError ? err.message : "Upload failed. Please try again.",
        );
        // Close the dialog so the error hint renders in the dropzone below.
        setPendingUploadFile(null);
      } finally {
        setUploading(false);
      }
    },
    [pendingUploadFile, listParams],
  );

  // -------- delete --------

  const handleRequestDelete = useCallback((document: Document) => {
    setDeleteError(null);
    setPendingDelete(document);
  }, []);

  const handleRequestEdit = useCallback((document: Document) => {
    setUpdateError(null);
    setPendingEditDocument(document);
    // Note: editingId is intentionally NOT set here; it marks the in-flight PATCH,
    // so the dialog's controls stay enabled until the user submits.
  }, []);

  const handleCancelDelete = useCallback(() => {
    if (deletingId) return;
    setPendingDelete(null);
    setDeleteError(null);
  }, [deletingId]);

  const handleCancelEdit = useCallback(() => {
    if (editingId) return;
    setPendingEditDocument(null);
    setEditingId(null);
    setUpdateError(null);
  }, [editingId]);

  const handleConfirmDelete = useCallback(async () => {
    if (!pendingDelete) return;
    setDeletingId(pendingDelete.id);
    setDeleteError(null);
    try {
      await documentsApi.remove(pendingDelete.id);
      setPendingDelete(null);
      const items = await documentsApi.list(listParams);
      setList({ status: "ready", documents: items });
    } catch (err) {
      setDeleteError(
        err instanceof APIError ? err.message : "Delete failed. Please try again.",
      );
      // Keep the dialog open so the user can retry or cancel.
    } finally {
      setDeletingId(null);
    }
  }, [pendingDelete, listParams]);

  const handleUpdateDocument = useCallback(async (payload: DocumentUpdate) => {
    if (!pendingEditDocument) return;
    setEditingId(pendingEditDocument.id);
    setUpdateError(null);
    try {
      await documentsApi.update(pendingEditDocument.id, payload);
      setPendingEditDocument(null);
      setEditingId(null);
      const items = await documentsApi.list(listParams);
      setList({ status: "ready", documents: items });
    } catch (err) {
      setUpdateError(
        err instanceof APIError ? err.message : "Update failed. Please try again.",
      );
    } finally {
      setEditingId(null);
    }
  }, [pendingEditDocument, listParams]);

  // -------- filter dropdown content --------

  const courses: Course[] =
    coursesState.status === "ready" ? coursesState.courses : [];

  const renderFilterPanel = () => (
    <section className={styles.filters} aria-label="Filter documents" data-testid="documents-filters">
      <div className={styles.filterField}>
        <label htmlFor="documents-filter-course" className={styles.filterLabel}>
          Course
        </label>
        <select
          id="documents-filter-course"
          className={styles.filterSelect}
          value={filters.course_id ?? ""}
          onChange={handleCourseFilterChange}
          data-testid="documents-filter-course"
        >
          <option value="">All courses</option>
          {courses.map((course) => (
            <option key={course.id} value={course.id}>
              {course.code ? `${course.code} — ${course.name}` : course.name}
            </option>
          ))}
        </select>
      </div>

      <div className={styles.filterField}>
        <label htmlFor="documents-filter-type" className={styles.filterLabel}>
          Document type
        </label>
        <select
          id="documents-filter-type"
          className={styles.filterSelect}
          value={filters.document_type ?? ""}
          onChange={handleTypeFilterChange}
          data-testid="documents-filter-type"
        >
          <option value="">All types</option>
          {DOCUMENT_TYPE_VALUES.map((value) => (
            <option key={value} value={value}>
              {DOCUMENT_TYPE_LABELS[value]}
            </option>
          ))}
        </select>
      </div>

      {filtersActive ? (
        <Button
          type="button"
          variant="ghost"
          onClick={handleClearFilters}
          className={styles.filterClear}
          data-testid="documents-filter-clear"
        >
          Clear filters
        </Button>
      ) : null}
    </section>
  );

  // -------- list content --------

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
            title={
              filtersActive
                ? "No documents match these filters"
                : "No documents yet"
            }
            description={
              filtersActive
                ? "Try clearing the filters or upload a new document that matches."
                : `Upload your first academic file to get started. Supported formats: ${SUPPORTED_FORMATS_LABEL}.`
            }
          />
        </div>
      );
    }

    return (
      <DocumentList
        documents={list.documents}
        deletingIds={new Set(deletingId ? [deletingId] : [])}
        onRequestDelete={handleRequestDelete}
        onRequestEdit={handleRequestEdit}
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

      {renderFilterPanel()}

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

      {pendingUploadFile ? (
        <DocumentUploadDetailsDialog
          file={pendingUploadFile}
          courses={courses}
          pending={uploading}
          onCancel={() => setPendingUploadFile(null)}
          onConfirm={handleUploadConfirm}
        />
      ) : null}

      {pendingEditDocument ? (
        <DocumentEditDialog
          document={pendingEditDocument}
          courses={courses}
          pending={editingId !== null}
          error={updateError}
          onCancel={handleCancelEdit}
          onConfirm={handleUpdateDocument}
        />
      ) : null}
    </div>
  );
}
