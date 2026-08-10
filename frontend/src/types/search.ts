import type { UUID } from "./api";
import type { RetrievalMode } from "./chat";

export interface RetrievedChunk {
  chunk_id: string;
  document_id?: UUID | null;
  text: string;
  score: number;
  page_number?: number | null;
  chunk_index: number;
  metadata: Record<string, unknown>;
}

export interface SearchRequest {
  query: string;
  top_k?: number;
  score_threshold?: number | null;
  document_id?: UUID | null;
  mode?: RetrievalMode;
}

export interface SearchResponse {
  results: RetrievedChunk[];
}
