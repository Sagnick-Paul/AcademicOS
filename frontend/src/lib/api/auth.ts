import { apiFetch, API_PATHS } from "./client";
import type { LoginPayload, RegisterPayload, TokenResponse, User } from "@/types";

export const authApi = {
  register: (payload: RegisterPayload) =>
    apiFetch<User>(API_PATHS.auth.register, { method: "POST", body: payload, auth: false }),

  login: (payload: LoginPayload) =>
    apiFetch<TokenResponse>(API_PATHS.auth.login, { method: "POST", body: payload, auth: false }),

  me: () => apiFetch<User>(API_PATHS.auth.me),
};
