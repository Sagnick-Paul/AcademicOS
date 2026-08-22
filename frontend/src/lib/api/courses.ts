import { apiFetch, API_PATHS } from "./client";
import type {
  Course,
  CourseCreate,
  CourseListResponse,
  CourseUpdate,
  Void,
} from "@/types";

/**
 * Course API.
 *
 * Mirrors the backend's `app/api/v1/endpoints/courses.py` surface.
 * Every call goes through the shared `apiFetch` so the bearer token,
 * error normalization, and timeout handling stay consistent with the
 * other API modules.
 */
export const coursesApi = {
  list: () => apiFetch<CourseListResponse>(API_PATHS.courses.list),

  create: (payload: CourseCreate) =>
    apiFetch<Course>(API_PATHS.courses.list, { method: "POST", body: payload }),

  get: (id: string) => apiFetch<Course>(API_PATHS.courses.byId(id)),

  update: (id: string, payload: CourseUpdate) =>
    apiFetch<Course>(API_PATHS.courses.byId(id), { method: "PATCH", body: payload }),

  remove: (id: string) =>
    apiFetch<Void>(API_PATHS.courses.byId(id), { method: "DELETE" }),
};
