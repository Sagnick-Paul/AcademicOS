"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/hooks/useAuth";
import { Button } from "@/components/ui/Button";
import { ErrorState } from "@/components/primitives/ErrorState";
import styles from "../login/form.module.css";

export function RegisterForm() {
  const { register } = useAuth();
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setPending(true);
    setError(null);
    try {
      await register({ full_name: fullName, email, password });
      router.replace("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create account");
    } finally {
      setPending(false);
    }
  }

  return (
    <form className={styles.card} onSubmit={onSubmit} noValidate>
      <h1 className={styles.title}>Create your account</h1>
      <p className={styles.lede}>It takes about thirty seconds.</p>

      <label className={styles.field}>
        <span className={styles.label}>Full name</span>
        <input
          required
          minLength={1}
          maxLength={255}
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          className={styles.input}
        />
      </label>

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
          autoComplete="new-password"
          required
          minLength={8}
          maxLength={128}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className={styles.input}
        />
      </label>

      {error ? (
        <ErrorState title="Could not create your account" description={error} />
      ) : null}

      <Button type="submit" variant="primary" fullWidth disabled={pending}>
        {pending ? "Creating…" : "Create account"}
      </Button>

      <div className={styles.foot}>
        Already have an account? <Link href="/login">Sign in</Link>
      </div>
    </form>
  );
}
