"use client";

import { Button } from "@/components/ui/Button";
import { fileTypeLabel } from "@/lib/constants/upload";
import { formatDate, formatFileSize } from "@/lib/utils/format";
import type { Document, DocumentUploadStatus } from "@/types";
import styles from "./DocumentCard.module.css";

interface DocumentCardProps {
  document: Document;
  /** True while this card's delete request is in flight. */
  deleting?: boolean;
  onRequestDelete: (document: Document) => void;
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
 */
export function DocumentCard({ document, deleting = false, onRequestDelete }: DocumentCardProps) {
  const handleDelete = () => onRequestDelete(document);

  return (
    <article className={styles.card} data-testid="document-card" data-document-id={document.id}>
      <header className={styles.header}>
        <div className={styles.titleRow}>
          <h3 className={styles.title} title={document.original_filename}>
            {document.original_filename}
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

      <footer className={styles.footer}>
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