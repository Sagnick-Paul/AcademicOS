"use client";

import { useEffect, useRef } from "react";
import { Button } from "@/components/ui/Button";
import styles from "./DeleteConfirmDialog.module.css";

interface DeleteConfirmDialogProps {
  /** Display name to show in the message. Empty string is allowed. */
  documentName: string;
  /** True while the delete request is in flight. */
  pending: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

/**
 * Confirmation dialog for deleting a document.
 *
 * Self-contained: traps focus on the cancel button on mount, closes
 * on Escape, and dispatches the parent's confirm/cancel callbacks.
 * The parent owns the request — this component never talks to the API.
 */
export function DeleteConfirmDialog({
  documentName,
  pending,
  onConfirm,
  onCancel,
}: DeleteConfirmDialogProps) {
  const cancelRef = useRef<HTMLButtonElement>(null);

  // Focus the cancel button on mount (safer default), restore on unmount.
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    cancelRef.current?.focus();
    return () => {
      previous?.focus?.();
    };
  }, []);

  // Close on Escape.
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
      data-testid="delete-confirm-backdrop"
    >
      <div
        className={styles.dialog}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="delete-confirm-title"
        aria-describedby="delete-confirm-description"
        data-testid="delete-confirm-dialog"
      >
        <h2 id="delete-confirm-title" className={styles.title}>
          Delete document?
        </h2>
        <p id="delete-confirm-description" className={styles.description}>
          {documentName ? (
            <>
              <strong>{documentName}</strong> will be permanently removed
              from your library.
            </>
          ) : (
            <>This document will be permanently removed from your library.</>
          )}{" "}
          This cannot be undone.
        </p>
        <div className={styles.actions}>
          <Button
            ref={cancelRef}
            type="button"
            variant="ghost"
            onClick={onCancel}
            disabled={pending}
            data-testid="delete-confirm-cancel"
          >
            Cancel
          </Button>
          <Button
            type="button"
            variant="danger"
            onClick={onConfirm}
            disabled={pending}
            data-testid="delete-confirm-confirm"
          >
            {pending ? "Deleting…" : "Delete"}
          </Button>
        </div>
      </div>
    </div>
  );
}