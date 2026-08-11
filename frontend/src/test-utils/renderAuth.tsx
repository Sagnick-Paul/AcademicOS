// Small helper for AuthContext + form tests. Mounts children under
// <AuthProvider> + a probe child that calls useAuth() and reports the
// latest value via the supplied callback on every render.
//
// Tests should assert AFTER bootstrap settles by waiting for
// status !== "loading" before reading `getContext()`.

import { render, type RenderResult } from "@testing-library/react";
import { type ReactNode } from "react";
import { AuthProvider, type AuthContextValue } from "@/lib/context/AuthContext";
import { useAuth } from "@/lib/hooks/useAuth";
import { APIError } from "@/types/api";

interface ProbeProps {
  onValue(value: AuthContextValue): void;
}

function Probe({ onValue }: ProbeProps) {
  const value = useAuth();
  onValue(value);
  return null;
}

export interface RenderAuthResult extends RenderResult {
  /** Returns the latest captured AuthContextValue. */
  context(): AuthContextValue;
}

export function renderAuth(
  onValue: (value: AuthContextValue) => void,
): RenderAuthResult {
  let last: AuthContextValue | null = null;
  const utils = render(
    <AuthProvider>
      <Probe
        onValue={(v) => {
          last = v;
          onValue(v);
        }}
      />
    </AuthProvider>,
  );
  const result = utils as RenderAuthResult;
  result.context = (): AuthContextValue => {
    if (!last) throw new Error("AuthProbe has not rendered yet");
    return last;
  };
  return result;
}

/** Convenience builder for an APIError the way apiFetch throws one. */
export function makeApiError(message: string, status: number): APIError {
  return new APIError(message, status, { detail: message });
}

// Re-export so test files only need a single test-utils import.
export type { AuthContextValue };
export type { ReactNode };
