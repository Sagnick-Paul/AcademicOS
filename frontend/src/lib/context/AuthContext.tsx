"use client";

import {
  createContext,
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { authApi } from "@/lib/api/auth";
import {
  clearStoredAuth,
  getStoredToken,
  setStoredToken,
  setStoredUserJSON,
} from "@/lib/auth/storage";
import type { LoginPayload, RegisterPayload, User } from "@/types";

export type AuthStatus = "loading" | "authenticated" | "unauthenticated";

export interface AuthContextValue {
  status: AuthStatus;
  user: User | null;
  accessToken: string | null;
  login(payload: LoginPayload): Promise<void>;
  register(payload: RegisterPayload): Promise<void>;
  logout(): void;
  refreshUser(): Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

interface ProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: ProviderProps) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<User | null>(null);

  // Bootstrap: if a token exists, validate it by calling /me.
  useEffect(() => {
    let cancelled = false;
    async function bootstrap() {
      const token = getStoredToken();
      if (!token) {
        if (!cancelled) setStatus("unauthenticated");
        return;
      }
      try {
        const fresh = await authApi.me();
        if (cancelled) return;
        setUser(fresh);
        setStoredUserJSON(fresh);
        setStatus("authenticated");
      } catch {
        // Token invalid/expired — drop it.
        clearStoredAuth();
        setStatus("unauthenticated");
      }
    }
    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (payload: LoginPayload) => {
    const token = await authApi.login(payload);
    setStoredToken(token.access_token);
    const fresh = await authApi.me();
    setUser(fresh);
    setStoredUserJSON(fresh);
    setStatus("authenticated");
  }, []);

  const register = useCallback(async (payload: RegisterPayload) => {
    await authApi.register(payload);
    await login({ email: payload.email, password: payload.password });
  }, [login]);

  const refreshUser = useCallback(async () => {
    const fresh = await authApi.me();
    setUser(fresh);
    setStoredUserJSON(fresh);
  }, []);

  const logout = useCallback(() => {
    clearStoredAuth();
    setUser(null);
    setStatus("unauthenticated");
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user,
      accessToken: getStoredToken(),
      login,
      register,
      logout,
      refreshUser,
    }),
    [status, user, login, register, logout, refreshUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
