"use client";

import { useId, useMemo, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import {
  COURSE_CODE_MAX,
  COURSE_DESCRIPTION_MAX,
  COURSE_NAME_MAX,
  hasCourseErrors,
  validateCourse,
} from "@/lib/constants/courses";
import type { Course, CourseCreate, CourseUpdate } from "@/types";
import styles from "./courses.module.css";

interface CourseFormProps {
  /** When editing, the course being edited. Omit to render a create form. */
  course?: Course;
  pending?: boolean;
  /** Backend or network error surfaced as a banner above the actions. */
  errorMessage?: string | null;
  onSubmit: (payload: CourseCreate | CourseUpdate) => void;
  onCancel?: () => void;
  /** Submit-button label, defaults to "Save". */
  submitLabel?: string;
}

/**
 * Course create / edit form. Pure presentation; the parent owns the
 * submit handler, the pending state, and any backend error message.
 *
 * Validation mirrors the backend's Pydantic constraints (length caps,
 * required name) so users see errors immediately. The backend remains
 * the source of truth — duplicate-name conflicts are surfaced via the
 * `errorMessage` prop.
 */
export function CourseForm({
  course,
  pending = false,
  errorMessage = null,
  onSubmit,
  onCancel,
  submitLabel,
}: CourseFormProps) {
  const nameId = useId();
  const codeId = useId();
  const descriptionId = useId();

  const [name, setName] = useState<string>(course?.name ?? "");
  const [code, setCode] = useState<string>(course?.code ?? "");
  const [description, setDescription] = useState<string>(course?.description ?? "");

  const errors = useMemo(
    () => validateCourse({ name, code, description }),
    [name, code, description],
  );
  const blockingErrors = hasCourseErrors(errors);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (blockingErrors) return;

    if (course) {
      // PATCH — only send fields the user actually changed. Anything
      // the user touched (including clearing) is sent; everything else
      // is omitted so the backend's omit-vs-null semantics work.
      const payload: CourseUpdate = {};
      const trimmedName = name.trim();
      if (trimmedName !== course.name) payload.name = trimmedName;
      const trimmedCode = code.trim();
      if ((trimmedCode || null) !== (course.code ?? null)) {
        payload.code = trimmedCode ? trimmedCode : null;
      }
      const trimmedDescription = description.trim();
      if ((trimmedDescription || null) !== (course.description ?? null)) {
        payload.description = trimmedDescription ? trimmedDescription : null;
      }
      onSubmit(payload);
    } else {
      // POST — required name plus whatever else was filled in.
      const payload: CourseCreate = {
        name: name.trim(),
      };
      if (code.trim()) payload.code = code.trim();
      else payload.code = null;
      if (description.trim()) payload.description = description.trim();
      else payload.description = null;
      onSubmit(payload);
    }
  };

  return (
    <form className={styles.form} onSubmit={handleSubmit} data-testid="course-form" noValidate>
      <div className={styles.formHeader}>
        <h3 className={styles.formTitle}>
          {course ? "Edit course" : "Create course"}
        </h3>
      </div>

      {errorMessage ? (
        <div className={styles.formError} role="alert" data-testid="course-form-error">
          {errorMessage}
        </div>
      ) : null}

      <div className={styles.field}>
        <label htmlFor={nameId} className={styles.label}>
          Name <span aria-hidden="true">*</span>
        </label>
        <input
          id={nameId}
          className={styles.input}
          type="text"
          value={name}
          onChange={(event) => setName(event.target.value)}
          disabled={pending}
          required
          aria-invalid={Boolean(errors.name)}
          aria-describedby={errors.name ? `${nameId}-error` : undefined}
          data-testid="course-form-name"
        />
        {errors.name ? (
          <span id={`${nameId}-error`} className={styles.fieldError} data-testid="course-form-name-error">
            {errors.name}
          </span>
        ) : (
          <span className={styles.fieldHint}>
            Up to {COURSE_NAME_MAX} characters.
          </span>
        )}
      </div>

      <div className={styles.field}>
        <label htmlFor={codeId} className={styles.label}>
          Code
        </label>
        <input
          id={codeId}
          className={styles.input}
          type="text"
          value={code}
          onChange={(event) => setCode(event.target.value)}
          disabled={pending}
          aria-invalid={Boolean(errors.code)}
          aria-describedby={errors.code ? `${codeId}-error` : undefined}
          data-testid="course-form-code"
        />
        {errors.code ? (
          <span id={`${codeId}-error`} className={styles.fieldError}>
            {errors.code}
          </span>
        ) : (
          <span className={styles.fieldHint}>
            Optional, up to {COURSE_CODE_MAX} characters.
          </span>
        )}
      </div>

      <div className={styles.field}>
        <label htmlFor={descriptionId} className={styles.label}>
          Description
        </label>
        <textarea
          id={descriptionId}
          className={styles.textarea}
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          disabled={pending}
          rows={3}
          aria-invalid={Boolean(errors.description)}
          aria-describedby={errors.description ? `${descriptionId}-error` : undefined}
          data-testid="course-form-description"
        />
        {errors.description ? (
          <span id={`${descriptionId}-error`} className={styles.fieldError}>
            {errors.description}
          </span>
        ) : (
          <span className={styles.fieldHint}>
            Optional, up to {COURSE_DESCRIPTION_MAX} characters.
          </span>
        )}
      </div>

      <div className={styles.formActions}>
        {onCancel ? (
          <Button
            type="button"
            variant="ghost"
            onClick={onCancel}
            disabled={pending}
            data-testid="course-form-cancel"
          >
            Cancel
          </Button>
        ) : null}
        <Button
          type="submit"
          variant="primary"
          disabled={pending || blockingErrors}
          data-testid="course-form-submit"
        >
          {pending ? "Saving…" : (submitLabel ?? "Save")}
        </Button>
      </div>
    </form>
  );
}
