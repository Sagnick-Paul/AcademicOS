"use client";

import { useId, useRef, useState, type ChangeEvent, type DragEvent } from "react";
import { Button } from "@/components/ui/Button";
import { ACCEPT_ATTRIBUTE, SUPPORTED_FORMATS_LABEL } from "@/lib/constants/upload";
import { cn } from "@/lib/utils/cn";
import styles from "./DocumentUpload.module.css";

interface DocumentUploadProps {
  /** Called with the chosen file. The component does not run the request itself. */
  onSelect: (file: File) => void;
  /** True while a parent-driven upload is in flight; disables the controls. */
  pending?: boolean;
  /** A short label for the currently-selected file (e.g. just-uploaded). */
  selectedName?: string | null;
  /** Optional message to show under the input (e.g. validation error). */
  hint?: string;
}

/**
 * Upload control. Renders a dropzone + click-to-browse file picker.
 * The component is purely a picker — it does not call the API. The
 * parent owns the upload request, the pending state, and the post-
 * upload refresh, so the entire lifecycle stays in one place.
 */
export function DocumentUpload({
  onSelect,
  pending = false,
  selectedName = null,
  hint,
}: DocumentUploadProps) {
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [localName, setLocalName] = useState<string | null>(null);

  const handleFiles = (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const file = files[0];
    setLocalName(file.name);
    onSelect(file);
  };

  const handleInputChange = (event: ChangeEvent<HTMLInputElement>) => {
    handleFiles(event.target.files);
    // Reset the input so selecting the same file twice still fires.
    event.target.value = "";
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragging(false);
    handleFiles(event.dataTransfer.files);
  };

  const handleDragOver = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragging(true);
  };

  const handleDragLeave = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragging(false);
  };

  const displayName = selectedName ?? localName;

  return (
    <div className={styles.root}>
      <div
        className={cn(
          styles.dropzone,
          dragging && styles.dropzoneActive,
          pending && styles.dropzonePending,
        )}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        data-testid="document-upload-dropzone"
      >
        <div className={styles.dropzoneContent}>
          <div className={styles.dropzoneTitle}>
            {pending ? "Uploading…" : "Drop a file or click to browse"}
          </div>
          <div className={styles.dropzoneSubtitle}>
            Supported: {SUPPORTED_FORMATS_LABEL}
          </div>
          {displayName ? (
            <div className={styles.selectedFile} data-testid="document-upload-selected">
              Selected: <span className={styles.selectedFileName}>{displayName}</span>
            </div>
          ) : null}
        </div>

        <input
          ref={inputRef}
          id={inputId}
          type="file"
          accept={ACCEPT_ATTRIBUTE}
          onChange={handleInputChange}
          disabled={pending}
          className={styles.fileInput}
          data-testid="document-upload-input"
        />
        <label htmlFor={inputId} className={styles.fileLabel}>
          <Button
            type="button"
            variant="primary"
            disabled={pending}
            onClick={() => inputRef.current?.click()}
            data-testid="document-upload-button"
          >
            {pending ? "Uploading…" : "Choose file"}
          </Button>
        </label>
      </div>

      {hint ? (
        <div className={styles.hint} role="status" data-testid="document-upload-hint">
          {hint}
        </div>
      ) : null}
    </div>
  );
}