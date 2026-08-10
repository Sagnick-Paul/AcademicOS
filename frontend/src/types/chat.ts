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
  created_at: string;
  updated_at: string;
}

export interface ChatSessionWithMessages extends ChatSession {
  messages: ChatMessageWithSources[];
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
}

export interface UpdateSessionPayload {
  title?: string;
}
