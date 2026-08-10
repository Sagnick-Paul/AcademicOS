import type { ReactNode } from "react";
import styles from "./layout.module.css";
import { Logo } from "@/components/ui/Logo";

interface Props {
  children: ReactNode;
}

export default function AuthLayout({ children }: Props) {
  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <Logo size="sm" />
      </header>
      <main className={styles.main}>{children}</main>
    </div>
  );
}
