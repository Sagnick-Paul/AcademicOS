"use client";

import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/Button";
import { DOCUMENT_TYPE_LABELS, DOCUMENT_TYPE_VALUES } from "@/types";
import type { Course, DocumentType, DocumentUploadOptions } from "@/types";
import styles from "./DocumentUploadDetailsDialog.module.css";

interface DocumentUploadDetailsDialogProps {
  file: File;
  courses: Course[];
  pending?: boolean;
  onConfirm: (options: DocumentUploadOptions) => void;
  onCancel: () => void;
}

export function DocumentUploadDetailsDialog({
  file,
  courses,
  pending = false,
  onConfirm,
  onCancel,
}: DocumentUploadDetailsDialogProps) {
  const cancelRef = useRef<HTMLButtonElement>(null);

  const [courseId, setCourseId] = useState<string>("");
  const [documentType, setDocumentType] = useState<DocumentType>(null);
  const [metadata, setMetadata] = useState({
    author: "",
    subject: "",
    semester: "",
    academic_year: "",
    tags: "",
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

    const options: DocumentUploadOptions = {
      course_id: courseId === "" ? undefined : courseId,
      document_type: documentType,
    };

    const tags = metadata.tags
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);

    if (
      metadata.author.trim() ||
      metadata.subject.trim() ||
      metadata.semester.trim() ||
      metadata.academic_year.trim() ||
      tags.length > 0
    ) {
      options.document_metadata = {
        author: metadata.author.trim() || null,
        subject: metadata.subject.trim() || null,
        semester: metadata.semester.trim() || null,
        academic_year: metadata.academic_year.trim() || null,
        tags,
      };
    }

    onConfirm(options);
  };

  return (
    <div
      className={styles.backdrop}
      onClick={handleBackdrop}
      role="presentation"
      data-testid="upload-details-backdrop"
    >
      <div
        className={styles.dialog}
        role="dialog"
        aria-modal="true"
        aria-labelledby="upload-details-title"
        data-testid="upload-details-dialog"
      >
        <h2 id="upload-details-title" className={styles.title}>
          Upload details
        </h2>

        <div className={styles.fileInfo}>
          <span className={styles.label}>File: </span>
          <strong>{file.name}</strong>
        </div>

        <form className={styles.form} onSubmit={handleSubmit}>
          <div className={styles.field}>
            <label htmlFor="upload-course" className={styles.label}>
              Course
            </label>
            <select
              id="upload-course"
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
            <label htmlFor="upload-type" className={styles.label}>
              Document type
            </label>
            <select
              id="upload-type"
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
              <label htmlFor="upload-author" className={styles.label}>
                Author
              </label>
              <input
                id="upload-author"
                className={styles.input}
                type="text"
                value={metadata.author}
                onChange={(e) => setMetadata((prev) => ({ ...prev, author: e.target.value }))}
                disabled={pending}
              />
            </div>
            <div className={styles.field}>
              <label htmlFor="upload-subject" className={styles.label}>
                Subject
              </label>
              <input
                id="upload-subject"
                className={styles.input}
                type="text"
                value={metadata.subject}
                onChange={(e) => setMetadata((prev) => ({ ...prev, subject: e.target.value }))}
                disabled={pending}
              />
            </div>
            <div className={styles.field}>
              <label htmlFor="upload-semester" className={styles.label}>
                Semester
              </label>
              <input
                id="upload-semester"
                className={styles.input}
                type="text"
                value={metadata.semester}
                onChange={(e) => setMetadata((prev) => ({ ...prev, semester: e.target.value }))}
                disabled={pending}
              />
            </div>
            <div className={styles.field}>
              <label htmlFor="upload-year" className={styles.label}>
                Academic Year
              </label>
              <input
                id="upload-year"
                className={styles.input}
                type="text"
                value={metadata.academic_year}
                onChange={(e) => setMetadata((prev) => ({ ...prev, academic_year: e.target.value }))}
                disabled={pending}
              />
            </div>
          </div>

          <div className={styles.field}>
            <label htmlFor="upload-tags" className={styles.label}>
              Tags (comma separated)
            </label>
            <input
              id="upload-tags"
              className={styles.input}
              type="text"
              value={metadata.tags}
              onChange={(e) => setMetadata((prev) => ({ ...prev, tags: e.target.value }))}
              disabled={pending}
              placeholder="e.g. important, exam-prep, final"
            />
          </div>

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
              {pending ? "Uploading…" : "Upload document"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
