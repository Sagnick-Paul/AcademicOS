"use client";

import { useEffect, useRef } from "react";
import { Button } from "@/components/ui/Button";
import styles from "../documents/DeleteConfirmDialog.module.css";

interface CourseDeleteDialogProps {
  courseName: string;
  pending: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

/**
 * Confirmation dialog for deleting a course. Reuses the existing
 * document-confirmation styles so the experience is consistent.
 */
export function CourseDeleteDialog({
  courseName,
  pending,
  onConfirm,
  onCancel,
}: CourseDeleteDialogProps) {
  const cancelRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    cancelRef.current?.focus();
    return () => {
      previous?.focus?.();
    };
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

  return (
    <div
      className={styles.backdrop}
      onClick={handleBackdrop}
      role="presentation"
      data-testid="course-delete-backdrop"
    >
      <div
        className={styles.dialog}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="course-delete-title"
        aria-describedby="course-delete-description"
        data-testid="course-delete-dialog"
      >
        <h2 id="course-delete-title" className={styles.title}>
          Delete course?
        </h2>
        <p id="course-delete-description" className={styles.description}>
          <strong>{courseName}</strong> will be permanently removed. Documents
          and chat sessions previously linked to this course will be
          unlinked. This cannot be undone.
        </p>
        <div className={styles.actions}>
          <Button
            ref={cancelRef}
            type="button"
            variant="ghost"
            onClick={onCancel}
            disabled={pending}
            data-testid="course-delete-cancel"
          >
            Cancel
          </Button>
          <Button
            type="button"
            variant="danger"
            onClick={onConfirm}
            disabled={pending}
            data-testid="course-delete-confirm"
          >
            {pending ? "Deleting…" : "Delete"}
          </Button>
        </div>
      </div>
    </div>
  );
}
