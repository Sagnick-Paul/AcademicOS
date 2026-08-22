"use client";

import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { fileTypeLabel } from "@/lib/constants/upload";
import { formatDate, formatFileSize } from "@/lib/utils/format";
import { DOCUMENT_TYPE_LABELS } from "@/types";
import type { Document, DocumentUploadStatus } from "@/types";
import styles from "./DocumentCard.module.css";

interface DocumentCardProps {
  document: Document;
  /** True while this card's delete request is in flight. */
  deleting?: boolean;
  /**
   * Optional lookup of course id → human label. When provided, the
   * card renders the course as a clickable link into `/courses/{id}`.
   * Without the map we just show the document's `course_id` as a
   * muted token so the UI still works when the parent didn't load
   * the courses.
   */
  courseLookup?: ReadonlyMap<string, string>;
  onRequestDelete: (document: Document) => void;
  onRequestEdit: (document: Document) => void;
}

const STATUS_LABEL: Record<DocumentUploadStatus, string> = {
  pending: "Pending",
  uploading: "Uploading",
  processing: "Processing",
  ready: "Ready",
  failed: "Failed",
};

const STATUS_CLASS: Record<DocumentUploadStatus, string> = {
  pending: styles.statusPending ?? "",
  uploading: styles.statusUploading ?? "",
  processing: styles.statusProcessing ?? "",
  ready: styles.statusReady ?? "",
  failed: styles.statusFailed ?? "",
};

/**
 * Single document card. Pure presentational; the parent owns the
 * delete handler and the per-card "deleting" flag so the panel can
 * disable the right buttons while a request is in flight.
 *
 * Phase 6B/6C/6D: shows course, document type, and key metadata fields
 * when present.
 */
export function DocumentCard({
  document,
  deleting = false,
  courseLookup,
  onRequestDelete,
  onRequestEdit,
}: DocumentCardProps) {
  const handleDelete = () => onRequestDelete(document);
  const handleEdit = () => onRequestEdit(document);
  const courseLabel = document.course_id
    ? courseLookup?.get(document.course_id)
    : null;
  const typeLabel = document.document_type
    ? DOCUMENT_TYPE_LABELS[document.document_type]
    : null;

  return (
    <article className={styles.card} data-testid="document-card" data-document-id={document.id}>
      <header className={styles.header}>
        <div className={styles.titleRow}>
          <h3 className={styles.title} title={document.original_filename}>
            <Link href={`/documents/${document.id}`} className={styles.titleLink} data-testid="document-card-title-link">
              {document.original_filename}
            </Link>
          </h3>
          <span
            className={`${styles.status} ${STATUS_CLASS[document.upload_status]}`}
            data-testid="document-card-status"
            data-status={document.upload_status}
          >
            {STATUS_LABEL[document.upload_status]}
          </span>
        </div>
        <div className={styles.metaRow}>
          <span className={styles.meta} data-testid="document-card-type">
            {fileTypeLabel(document.file_type)}
          </span>
          <span className={styles.metaDot} aria-hidden="true">
            •
          </span>
          <span className={styles.meta} data-testid="document-card-size">
            {formatFileSize(document.file_size)}
          </span>
          <span className={styles.metaDot} aria-hidden="true">
            •
          </span>
          <span className={styles.meta} data-testid="document-card-date">
            Uploaded {formatDate(document.created_at)}
          </span>
        </div>
      </header>

      <dl className={styles.badgeRow} aria-label="Document classification">
        <Badge
          label="Course"
          value={document.course_id}
          display={courseLabel ?? (document.course_id ? "Linked" : null)}
          emptyText="Uncoursed"
          testId="document-card-course"
        />
        <Badge
          label="Type"
          value={document.document_type}
          display={typeLabel}
          emptyText="Untyped"
          testId="document-card-document-type"
        />
        <Badge
          label="Author"
          value={document.document_metadata?.author ?? null}
          display={document.document_metadata?.author ?? null}
          emptyText="—"
          testId="document-card-metadata-author"
        />
        <Badge
          label="Subject"
          value={document.document_metadata?.subject ?? null}
          display={document.document_metadata?.subject ?? null}
          emptyText="—"
          testId="document-card-metadata-subject"
        />
      </dl>

      {document.document_metadata?.tags && document.document_metadata.tags.length > 0 ? (
        <ul className={styles.tagList} aria-label="Tags" data-testid="document-card-tags">
          {document.document_metadata.tags.map((tag) => (
            <li key={tag} className={styles.tag} data-testid="document-card-tag">
              {tag}
            </li>
          ))}
        </ul>
      ) : null}

      {document.course_id ? (
        <div className={styles.courseLinkRow}>
          <Link
            href={`/courses/${document.course_id}`}
            className={styles.courseLink}
            data-testid="document-card-course-link"
          >
            Open course
          </Link>
        </div>
      ) : null}

      <footer className={styles.footer}>
        <Button
          type="button"
          variant="ghost"
          onClick={handleEdit}
          disabled={deleting}
          data-testid="document-card-edit"
        >
          Edit
        </Button>
        <Button
          variant="danger"
          type="button"
          onClick={handleDelete}
          disabled={deleting}
          data-testid="document-card-delete"
        >
          {deleting ? "Deleting…" : "Delete"}
        </Button>
      </footer>
    </article>
  );
}

interface BadgeProps {
  label: string;
  value: unknown;
  display: string | null;
  emptyText: string;
  testId: string;
}

function Badge({ label, value, display, emptyText, testId }: BadgeProps) {
  const isEmpty = value === null || value === undefined || value === "";
  return (
    <div className={styles.badge}>
      <dt className={styles.badgeLabel}>{label}</dt>
      <dd
        className={isEmpty ? styles.badgeEmpty : styles.badgeValue}
        data-testid={testId}
        data-empty={isEmpty ? "true" : "false"}
      >
        {display ?? emptyText}
      </dd>
    </div>
  );
}
