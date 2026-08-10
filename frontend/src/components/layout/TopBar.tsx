"use client";

import { Logo } from "@/components/ui/Logo";
import styles from "./TopBar.module.css";

interface Props {
  onToggleSidebar(): void;
}

export function TopBar({ onToggleSidebar }: Props) {
  return (
    <header className={styles.bar} role="banner">
      <button
        type="button"
        aria-label="Open navigation"
        className={styles.menuButton}
        onClick={onToggleSidebar}
      >
        {/* 16x16 hamburger — pure CSS, no asset. */}
        <svg
          width="16"
          height="16"
          viewBox="0 0 16 16"
          aria-hidden="true"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
        >
          <path d="M2 4h12M2 8h12M2 12h12" />
        </svg>
      </button>
      <div className={styles.title}>
        <Logo size="sm" />
      </div>
    </header>
  );
}
