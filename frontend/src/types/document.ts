import type { UUID } from "./api";

export type DocumentUploadStatus = "pending" | "uploading" | "processing" | "ready" | "failed";

/**
 * Academic classification of a Document.
 *
 * Phase 6C. Stored as the raw string value (`lecture_notes`,
 * `textbook`, ...) on the wire so the backend can add new values
 * without breaking older clients. The frontend uses a string-union
 * (not a TS `enum`) to avoid the runtime-cost + reverse-mapping
 * pitfalls of `enum`, and to make exhaustiveness checks trivial.
 *
 * `null` means "uncategorised" — either a legacy pre-6C row or a row
 * whose type was explicitly cleared.
 */
export type DocumentType =
  | "lecture_notes"
  | "textbook"
  | "presentation"
  | "assignment"
  | "previous_year_question"
  | "reference"
  | "other"
  | null;

export const DOCUMENT_TYPE_VALUES = [
  "lecture_notes",
  "textbook",
  "presentation",
  "assignment",
  "previous_year_question",
  "reference",
  "other",
] as const satisfies readonly DocumentType[];

/** Human-readable label for the UI. Backend values stay canonical. */
export const DOCUMENT_TYPE_LABELS: Record<NonNullable<DocumentType>, string> = {
  lecture_notes: "Lecture Notes",
  textbook: "Textbook",
  presentation: "Presentation",
  assignment: "Assignment",
  previous_year_question: "Previous Year Question",
  reference: "Reference",
  other: "Other",
};

/** Structured academic metadata attached to a Document. Phase 6C. */
export interface DocumentMetadata {
  author?: string | null;
  subject?: string | null;
  semester?: string | null;
  academic_year?: string | null;
  tags?: string[] | null;
}

export interface Document {
  id: UUID;
  owner_id: UUID;
  filename: string;
  original_filename: string;
  file_type: string;
  file_size: number;
  storage_path: string;
  upload_status: DocumentUploadStatus;
  /** Phase 6B: optional course link. `null` = uncoursed. */
  course_id: UUID | null;
  /** Phase 6C: academic classification. `null` = uncategorised. */
  document_type: DocumentType;
  /** Phase 6C: structured metadata. `null` = none provided. */
  document_metadata: DocumentMetadata | null;
  created_at: string;
  updated_at: string;
}

/**
 * Payload for `PATCH /documents/{id}`.
 *
 * The frontend distinguishes three states for every field:
 *
 *   - key absent    → "leave alone" (don't send the key at all)
 *   - key present, value === null → "explicitly clear" (send null)
 *   - key present, value !== null → "set to this value"
 *
 * The backend uses Pydantic's `model_fields_set` to detect the absent
 * case, so a normal `undefined` key in this interface MUST be stripped
 * before the request body is serialized (see `toDocumentUpdateBody`).
 */
export interface DocumentUpdate {
  filename?: string;
  file_type?: string;
  upload_status?: DocumentUploadStatus;
  course_id?: UUID | null;
  document_type?: DocumentType;
  document_metadata?: DocumentMetadata | null;
}

/**
 * Options passed to `documentsApi.upload()` alongside the raw `File`.
 * All fields are optional — the user may skip course/type during upload.
 */
export interface DocumentUploadOptions {
  course_id?: string;
  document_type?: DocumentType;
  document_metadata?: DocumentMetadata;
}
