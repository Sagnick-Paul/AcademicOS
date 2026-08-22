import { apiFetch, API_PATHS } from "./client";
import { stripUndefined } from "@/lib/utils/patch";
import type {
  ChatRequest,
  ChatResponse,
  ChatSession,
  ChatSessionWithMessages,
  CreateSessionPayload,
  SendMessagePayload,
  SendMessageResponse,
  UpdateSessionPayload,
  UUID,
  Void,
} from "@/types";

export const chatApi = {
  oneShot: (payload: ChatRequest) =>
    apiFetch<ChatResponse>(API_PATHS.chat.oneShot, { method: "POST", body: payload }),

  createSession: (payload: CreateSessionPayload) =>
    apiFetch<ChatSession>(API_PATHS.chat.sessions, {
      method: "POST",
      body: stripUndefined(payload as Record<string, unknown>),
    }),

  listSessions: (params?: { course_id?: UUID }) => {
    const search = new URLSearchParams();
    if (params?.course_id !== undefined) search.set("course_id", params.course_id);
    const qs = search.toString();
    return apiFetch<ChatSession[]>(`${API_PATHS.chat.sessions}${qs ? `?${qs}` : ""}`);
  },

  getSession: (id: string) => apiFetch<ChatSessionWithMessages>(API_PATHS.chat.sessionById(id)),

  updateSession: (id: string, payload: UpdateSessionPayload) =>
    apiFetch<ChatSession>(API_PATHS.chat.sessionById(id), {
      method: "PATCH",
      body: stripUndefined(payload as Record<string, unknown>),
    }),

  deleteSession: (id: string) =>
    apiFetch<Void>(API_PATHS.chat.sessionById(id), { method: "DELETE" }),

  sendMessage: (id: string, payload: SendMessagePayload) =>
    apiFetch<SendMessageResponse>(API_PATHS.chat.sendMessage(id), {
      method: "POST",
      body: payload,
    }),
};
