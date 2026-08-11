"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/hooks/useAuth";
import { LoadingState } from "@/components/primitives/LoadingState";

/**
 * Root entry point — routes the user based on authentication state.
 *
 * - `loading` → wait (no flicker, no redirect loop)
 * - `authenticated` → /dashboard
 * - `unauthenticated` → /login
 *
 * Spec §15: do NOT introduce routing loops. The `(app)/layout.tsx`
 * already bounces unauthenticated users to /login, so `/` simply
 * acts as a convenience that mirrors the auth state.
 */
export default function HomePage() {
  const { status } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (status === "authenticated") {
      router.replace("/dashboard");
    } else if (status === "unauthenticated") {
      router.replace("/login");
    }
  }, [status, router]);

  // While status === "loading" we render a neutral loading state —
  // never the marketing hero — so the redirect fires on first paint.
  if (status !== "authenticated" && status !== "unauthenticated") {
    return <LoadingState label="Loading AcademicOS…" />;
  }

  // Once status resolves we render nothing; the redirect in useEffect
  // takes over on the next paint.
  return null;
}
