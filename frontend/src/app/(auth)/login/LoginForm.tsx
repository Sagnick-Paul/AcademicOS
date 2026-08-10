"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/hooks/useAuth";
import { Button } from "@/components/ui/Button";
import { ErrorState } from "@/components/primitives/ErrorState";
import styles from "./form.module.css";

export function LoginForm() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setPending(true);
    setError(null);
    try {
      await login({ email, password });
      router.replace("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-in failed");
    } finally {
      setPending(false);
    }
  }

  return (
    <form className={styles.card} onSubmit={onSubmit} noValidate>
      <h1 className={styles.title}>Sign in</h1>
      <p className={styles.lede}>Use your AcademicOS account.</p>

      <label className={styles.field}>
        <span className={styles.label}>Email</span>
        <input
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className={styles.input}
        />
      </label>

      <label className={styles.field}>
        <span className={styles.label}>Password</span>
        <input
          type="password"
          autoComplete="current-password"
          required
          minLength={8}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className={styles.input}
        />
      </label>

      {error ? <ErrorState title="Could not sign you in" description={error} /> : null}

      <Button type="submit" variant="primary" fullWidth disabled={pending}>
        {pending ? "Signing in…" : "Sign in"}
      </Button>

      <div className={styles.foot}>
        New here? <Link href="/register">Create an account</Link>
      </div>
    </form>
  );
}
