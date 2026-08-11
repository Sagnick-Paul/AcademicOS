import { apiFetch, API_PATHS } from "./client";
import type {
  ChatRequest,
  ChatResponse,
  ChatSession,
  ChatSessionWithMessages,
  CreateSessionPayload,
  SendMessagePayload,
  SendMessageResponse,
  UpdateSessionPayload,
  Void,
} from "@/types";

export const chatApi = {
  oneShot: (payload: ChatRequest) =>
    apiFetch<ChatResponse>(API_PATHS.chat.oneShot, { method: "POST", body: payload }),

  createSession: (payload: CreateSessionPayload) =>
    apiFetch<ChatSession>(API_PATHS.chat.sessions, { method: "POST", body: payload }),

  listSessions: () => apiFetch<ChatSession[]>(API_PATHS.chat.sessions),

  getSession: (id: string) => apiFetch<ChatSessionWithMessages>(API_PATHS.chat.sessionById(id)),

  updateSession: (id: string, payload: UpdateSessionPayload) =>
    apiFetch<ChatSession>(API_PATHS.chat.sessionById(id), { method: "PATCH", body: payload }),

  deleteSession: (id: string) =>
    apiFetch<Void>(API_PATHS.chat.sessionById(id), { method: "DELETE" }),

  sendMessage: (id: string, payload: SendMessagePayload) =>
    apiFetch<SendMessageResponse>(API_PATHS.chat.sendMessage(id), {
      method: "POST",
      body: payload,
    }),
};
