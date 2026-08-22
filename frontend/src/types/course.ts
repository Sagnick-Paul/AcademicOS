import type { UUID } from "./api";

/**
 * Academic course — a folder-like grouping the user attaches documents
 * and chat sessions to. Phase 6A (backend) introduces the CRUD surface;
 * Phase 6D exposes it through the frontend.
 */
export interface Course {
  id: UUID;
  owner_id: UUID;
  name: string;
  code: string | null;
  description: string | null;
  created_at: string;
  updated_at: string;
}

/** Payload for `POST /courses`. `owner_id` is set by the backend. */
export interface CourseCreate {
  name: string;
  code?: string | null;
  description?: string | null;
}

/**
 * Payload for `PATCH /courses/{id}`. Every field is optional; the
 * backend distinguishes "omitted" from "explicit null" using
 * Pydantic's `model_fields_set` on the server.
 *
 * The frontend sends a key only when the user explicitly touched it.
 */
export interface CourseUpdate {
  name?: string;
  code?: string | null;
  description?: string | null;
}

/** Envelope returned by `GET /courses`. */
export interface CourseListResponse {
  items: Course[];
}
