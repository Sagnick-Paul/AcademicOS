import { apiFetch, API_PATHS } from "./client";
import type { Document, PageParams, Void } from "@/types";

export const documentsApi = {
  list: (params?: PageParams) => {
    const search = new URLSearchParams();
    if (params?.skip !== undefined) search.set("skip", String(params.skip));
    if (params?.limit !== undefined) search.set("limit", String(params.limit));
    const qs = search.toString();
    return apiFetch<Document[]>(`${API_PATHS.documents.list}${qs ? `?${qs}` : ""}`);
  },

  upload: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return apiFetch<Document>(API_PATHS.documents.upload, {
      method: "POST",
      formData,
    });
  },

  get: (id: string) => apiFetch<Document>(API_PATHS.documents.byId(id)),

  remove: (id: string) =>
    apiFetch<Void>(API_PATHS.documents.byId(id), { method: "DELETE" }),
};
