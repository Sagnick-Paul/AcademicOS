import type { UUID } from "./api";

export interface User {
  id: UUID;
  full_name: string;
  email: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string; // ISO-8601 from datetime
  updated_at: string;
}

export interface RegisterPayload {
  full_name: string;
  email: string;
  password: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: "bearer";
}
