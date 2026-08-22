import type { UUID } from "./api";

export type ChatRole = "user" | "assistant" | "system";
export type RetrievalMode = "semantic" | "hybrid";

export interface ChatMessageSource {
  id: UUID;
  message_id: UUID;
  document_id: UUID;
  chunk_id: string;
  position: number;
  page_number?: number | null;
  slide_number?: number | null;
  score?: number | null;
  snippet?: string | null;
}

export interface ChatMessage {
  id: UUID;
  session_id: UUID;
  role: ChatRole;
  content: string;
  created_at: string;
}

export interface ChatMessageWithSources extends ChatMessage {
  sources: ChatMessageSource[];
}

export interface ChatSession {
  id: UUID;
  user_id: UUID;
  title: string;
  /** Phase 6B: optional course link. `null` = uncoursed. */
  course_id: UUID | null;
  /** Phase 6E: optional document link. `null` = undocumented. */
  document_id: UUID | null;
  created_at: string;
  updated_at: string;
}

/** A message as it appears inside a session history payload. The
 *  backend persists user messages without a `sources` field, so the
 *  history is a mix of both shapes — we widen to a union here and let
 *  consumers narrow at the rendering site. */
export type ChatSessionMessage = ChatMessage | ChatMessageWithSources;

export interface ChatSessionWithMessages extends ChatSession {
  messages: ChatSessionMessage[];
}

export interface ChatSource {
  index: number;
  chunk_id: string;
  document_id?: UUID | null;
  document_title?: string | null;
  page_number?: number | null;
  chunk_index: number;
  score: number;
  snippet: string;
}

export interface ChatRequest {
  query: string;
  document_id?: UUID | null;
  mode?: RetrievalMode;
  top_k?: number;
  score_threshold?: number | null;
  temperature?: number;
  max_output_tokens?: number;
}

export interface ChatResponse {
  answer: string;
  sources: ChatSource[];
  model: string;
  retrieval_mode: RetrievalMode;
  prompt_tokens?: number | null;
  completion_tokens?: number | null;
}

export interface SendMessagePayload {
  query: string;
  document_id?: UUID | null;
  mode?: RetrievalMode;
  top_k?: number;
  score_threshold?: number | null;
  temperature?: number;
  max_output_tokens?: number;
}

export interface SendMessageResponse {
  user_message: ChatMessage;
  assistant_message: ChatMessageWithSources;
  model: string;
  retrieval_mode: RetrievalMode;
  prompt_tokens?: number | null;
  completion_tokens?: number | null;
}

export interface CreateSessionPayload {
  title?: string;
  initial_query?: string;
  /** Phase 6B: optional course link. */
  course_id?: UUID | null;
  /** Phase 6E: optional document link. */
  document_id?: UUID | null;
}

export interface UpdateSessionPayload {
  title?: string;
  /** Phase 6B: course link. `null` = unlink. Omit = leave alone. */
  course_id?: UUID | null;
  /** Phase 6E: document link. `null` = unlink. Omit = leave alone. */
  document_id?: UUID | null;
}
