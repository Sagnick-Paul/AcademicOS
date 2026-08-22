import { apiFetch, API_PATHS } from "./client";
import type {
  Document,
  DocumentMetadata,
  DocumentType,
  DocumentUpdate,
  PageParams,
  UUID,
  Void,
} from "@/types";
import { stripUndefined } from "@/lib/utils/patch";

export interface DocumentListParams extends PageParams {
  /** Phase 6B: filter to documents belonging to this course. */
  course_id?: UUID;
  /** Phase 6C: filter to documents with this academic classification. */
  document_type?: DocumentType;
}

export interface DocumentUploadOptions {
  /** Optional course to attach the new document to. */
  course_id?: UUID;
  /** Optional academic classification. */
  document_type?: DocumentType;
  /**
   * Optional metadata blob. Serialised to a JSON-encoded string the
   * backend parses from the form. The backend performs its own
   * normalisation (whitespace-trim, dedup tags, drop empties).
   */
  document_metadata?: DocumentMetadata;
}

/**
 * Document API.
 *
 * Mirrors the backend's `app/api/v1/endpoints/documents.py` surface.
 * Phase 6B/6C additions:
 *
 *   - `list()` accepts `course_id` and `document_type` filters.
 *   - `upload()` accepts an `options` object so the file picker still
 *     takes a single File argument (preserving the existing test
 *     surface) while new fields travel in a separate form field.
 *   - `update()` accepts a `DocumentUpdate` and strips `undefined`
 *     keys before the request body is serialised, so the backend's
 *     omit-vs-null semantics work as designed.
 */
export const documentsApi = {
  list: (params?: DocumentListParams) => {
    const search = new URLSearchParams();
    if (params?.skip !== undefined) search.set("skip", String(params.skip));
    if (params?.limit !== undefined) search.set("limit", String(params.limit));
    if (params?.course_id !== undefined) search.set("course_id", params.course_id);
    if (params?.document_type !== undefined && params.document_type !== null) {
      search.set("document_type", params.document_type);
    }
    const qs = search.toString();
    return apiFetch<Document[]>(`${API_PATHS.documents.list}${qs ? `?${qs}` : ""}`);
  },

  upload: (file: File, options: DocumentUploadOptions = {}) => {
    const formData = new FormData();
    formData.append("file", file);
    if (options.course_id !== undefined) {
      formData.append("course_id", options.course_id);
    }
    if (options.document_type !== undefined && options.document_type !== null) {
      formData.append("document_type", options.document_type);
    }
    if (options.document_metadata !== undefined) {
      // The backend expects a JSON-encoded string (FastAPI Form field)
      // and parses it into a Pydantic model itself.
      formData.append("document_metadata", JSON.stringify(options.document_metadata));
    }
    return apiFetch<Document>(API_PATHS.documents.upload, {
      method: "POST",
      formData,
    });
  },

  get: (id: string) => apiFetch<Document>(API_PATHS.documents.byId(id)),

  update: (id: string, payload: DocumentUpdate) =>
    apiFetch<Document>(API_PATHS.documents.byId(id), {
      method: "PATCH",
      body: stripUndefined(payload as Record<string, unknown>),
    }),

  remove: (id: string) =>
    apiFetch<Void>(API_PATHS.documents.byId(id), { method: "DELETE" }),
};
