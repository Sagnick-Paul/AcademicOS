import { apiFetch, API_PATHS } from "./client";
import type { SearchRequest, SearchResponse } from "@/types";

export const searchApi = {
  search: (payload: SearchRequest) =>
    apiFetch<SearchResponse>(API_PATHS.search, { method: "POST", body: payload }),
};
