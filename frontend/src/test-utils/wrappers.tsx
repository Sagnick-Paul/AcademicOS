// Wrapper that supplies a stubbed AuthContext value to the form under
// test. We don't mount a real <AuthProvider> here — the forms only call
// useAuth(), and we want test-controlled success/failure without going
// through the bootstrap path.

import { render, type RenderResult } from "@testing-library/react";
import { type ReactNode } from "react";
import { AuthContext, type AuthContextValue } from "@/lib/context/AuthContext";

export function renderWithAuth(
  ui: ReactNode,
  overrides: Partial<AuthContextValue> = {},
): RenderResult {
  const baseValue: AuthContextValue = {
    status: "unauthenticated",
    user: null,
    accessToken: null,
    login: async () => undefined,
    register: async () => undefined,
    logout: () => undefined,
    refreshUser: async () => undefined,
    ...overrides,
  };
  return render(
    <AuthContext.Provider value={baseValue}>{ui}</AuthContext.Provider>,
  );
}
