"use client";

import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";
import { useAuth } from "@/lib/hooks/useAuth";

interface Props {
  children: ReactNode;
}

/** Client-side guard for protected routes. */
export function RequireAuth({ children }: Props) {
  const { status } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/login");
    }
  }, [status, router]);

  if (status === "loading" || status === "unauthenticated") {
    // Render nothing — keeps the layout stable, avoids flicker.
    return null;
  }
  return <>{children}</>;
}

/** Inverse guard: redirect authenticated users away from /login, /register. */
export function RedirectIfAuthed({ children }: Props) {
  const { status } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (status === "authenticated") {
      router.replace("/dashboard");
    }
  }, [status, router]);

  if (status === "loading" || status === "authenticated") return null;
  return <>{children}</>;
}
