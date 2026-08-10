import Link from "next/link";
import { AppShell } from "@/components/layout/AppShell";
import { PageContainer } from "@/components/layout/PageContainer";
import { Button } from "@/components/ui/Button";
import { Logo } from "@/components/ui/Logo";
import styles from "./page.module.css";

export default function HomePage() {
  return (
    <AppShell>
      <PageContainer>
        <section className={styles.hero}>
          <Logo size="md" />
          <h1 className={styles.title}>
            Your AI-powered academic operating system.
          </h1>
          <p className={styles.lede}>
            Upload papers, ask grounded questions, and study with citations —
            all from one calm workspace.
          </p>
          <div className={styles.actions}>
            <Link href="/register">
              <Button variant="primary">Create account</Button>
            </Link>
            <Link href="/login">
              <Button variant="secondary">Sign in</Button>
            </Link>
          </div>
        </section>
      </PageContainer>
    </AppShell>
  );
}
