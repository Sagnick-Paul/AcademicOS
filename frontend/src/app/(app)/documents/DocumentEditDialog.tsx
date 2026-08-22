"use client";

import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/Button";
import { DOCUMENT_TYPE_LABELS, DOCUMENT_TYPE_VALUES } from "@/types";
import type { Course, Document, DocumentType, DocumentUpdate } from "@/types";
import styles from "./DocumentEditDialog.module.css";

interface DocumentEditDialogProps {
  document: Document;
  courses: Course[];
  pending?: boolean;
  error?: string | null;
  onConfirm: (payload: DocumentUpdate) => void;
  onCancel: () => void;
}

export function DocumentEditDialog({
  document,
  courses,
  pending = false,
  error = null,
  onConfirm,
  onCancel,
}: DocumentEditDialogProps) {
  const cancelRef = useRef<HTMLButtonElement>(null);

  const [courseId, setCourseId] = useState<string>(document.course_id ?? "");
  const [documentType, setDocumentType] = useState<DocumentType>(document.document_type);
  const [metadata, setMetadata] = useState({
    author: document.document_metadata?.author ?? "",
    subject: document.document_metadata?.subject ?? "",
    semester: document.document_metadata?.semester ?? "",
    academic_year: document.document_metadata?.academic_year ?? "",
    tags: document.document_metadata?.tags?.join(", ") ?? "",
  });

  useEffect(() => {
    cancelRef.current?.focus();
  }, []);

  useEffect(() => {
    function handleKey(event: KeyboardEvent) {
      if (event.key === "Escape" && !pending) onCancel();
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [onCancel, pending]);

  const handleBackdrop = (event: React.MouseEvent<HTMLDivElement>) => {
    if (event.target === event.currentTarget && !pending) onCancel();
  };

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();

    const payload: DocumentUpdate = {};

    // Course: omit if unchanged, null if cleared
    if (courseId !== (document.course_id ?? "")) {
      payload.course_id = courseId === "" ? null : courseId;
    }

    // Type: omit if unchanged, null if cleared
    if (documentType !== document.document_type) {
      payload.document_type = documentType;
    }

    // Metadata: handle complex merge
    const updatedMetadata = {
      author: metadata.author.trim() || null,
      subject: metadata.subject.trim() || null,
      semester: metadata.semester.trim() || null,
      academic_year: metadata.academic_year.trim() || null,
      tags: metadata.tags
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean),
    };

    // Simple check: did any metadata field change?
    const hasMetadataChanged =
      updatedMetadata.author !== (document.document_metadata?.author ?? null) ||
      updatedMetadata.subject !== (document.document_metadata?.subject ?? null) ||
      updatedMetadata.semester !== (document.document_metadata?.semester ?? null) ||
      updatedMetadata.academic_year !== (document.document_metadata?.academic_year ?? null) ||
      JSON.stringify(updatedMetadata.tags) !== JSON.stringify(document.document_metadata?.tags ?? []);

    if (hasMetadataChanged) {
      payload.document_metadata = updatedMetadata;
    }

    onConfirm(payload);
  };

  return (
    <div
      className={styles.backdrop}
      onClick={handleBackdrop}
      role="presentation"
      data-testid="document-edit-backdrop"
    >
      <div
        className={styles.dialog}
        role="dialog"
        aria-modal="true"
        aria-labelledby="document-edit-title"
        data-testid="document-edit-dialog"
      >
        <h2 id="document-edit-title" className={styles.title}>
          Edit document
        </h2>

        <form className={styles.form} onSubmit={handleSubmit}>
          <div className={styles.field}>
            <label htmlFor="edit-course" className={styles.label}>
              Course
            </label>
            <select
              id="edit-course"
              className={styles.select}
              value={courseId}
              onChange={(e) => setCourseId(e.target.value)}
              disabled={pending}
            >
              <option value="">No course</option>
              {courses.map((course) => (
                <option key={course.id} value={course.id}>
                  {course.code ? `${course.code} — ${course.name}` : course.name}
                </option>
              ))}
            </select>
          </div>

          <div className={styles.field}>
            <label htmlFor="edit-type" className={styles.label}>
              Document type
            </label>
            <select
              id="edit-type"
              className={styles.select}
              value={documentType ?? ""}
              onChange={(e) => setDocumentType(e.target.value as DocumentType)}
              disabled={pending}
            >
              <option value="">Untyped</option>
              {DOCUMENT_TYPE_VALUES.map((val) => (
                <option key={val} value={val}>
                  {DOCUMENT_TYPE_LABELS[val]}
                </option>
              ))}
            </select>
          </div>

          <div className={styles.metadataGrid}>
            <div className={styles.field}>
              <label htmlFor="edit-author" className={styles.label}>
                Author
              </label>
              <input
                id="edit-author"
                className={styles.input}
                type="text"
                value={metadata.author}
                onChange={(e) => setMetadata((prev) => ({ ...prev, author: e.target.value }))}
                disabled={pending}
              />
            </div>
            <div className={styles.field}>
              <label htmlFor="edit-subject" className={styles.label}>
                Subject
              </label>
              <input
                id="edit-subject"
                className={styles.input}
                type="text"
                value={metadata.subject}
                onChange={(e) => setMetadata((prev) => ({ ...prev, subject: e.target.value }))}
                disabled={pending}
              />
            </div>
            <div className={styles.field}>
              <label htmlFor="edit-semester" className={styles.label}>
                Semester
              </label>
              <input
                id="edit-semester"
                className={styles.input}
                type="text"
                value={metadata.semester}
                onChange={(e) => setMetadata((prev) => ({ ...prev, semester: e.target.value }))}
                disabled={pending}
              />
            </div>
            <div className={styles.field}>
              <label htmlFor="edit-year" className={styles.label}>
                Academic Year
              </label>
              <input
                id="edit-year"
                className={styles.input}
                type="text"
                value={metadata.academic_year}
                onChange={(e) => setMetadata((prev) => ({ ...prev, academic_year: e.target.value }))}
                disabled={pending}
              />
            </div>
          </div>

          <div className={styles.field}>
            <label htmlFor="edit-tags" className={styles.label}>
              Tags (comma separated)
            </label>
            <input
              id="edit-tags"
              className={styles.input}
              type="text"
              value={metadata.tags}
              onChange={(e) => setMetadata((prev) => ({ ...prev, tags: e.target.value }))}
              disabled={pending}
              placeholder="e.g. important, exam-prep, final"
            />
          </div>

          {error ? (
            <div className={styles.error} role="alert" data-testid="document-edit-error">
              {error}
            </div>
          ) : null}

          <div className={styles.actions}>
            <Button
              ref={cancelRef}
              type="button"
              variant="ghost"
              onClick={onCancel}
              disabled={pending}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              disabled={pending}
            >
              {pending ? "Saving…" : "Save changes"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
