"use client";

import { useEffect, useState, type ReactNode } from "react";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import styles from "./AppShell.module.css";

interface Props {
  children: ReactNode;
}

export function AppShell({ children }: Props) {
  const [open, setOpen] = useState(false);

  // Close the mobile drawer on route change (resize to desktop too).
  useEffect(() => {
    const mq = window.matchMedia("(min-width: 900px)");
    const onChange = (e: MediaQueryListEvent) => {
      if (e.matches) setOpen(false);
    };
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  // ESC closes the drawer.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <div className={styles.shell}>
      <Sidebar open={open} onClose={() => setOpen(false)} />
      <div className={styles.main}>
        <div className={styles.mobileOnlyTopBar}>
          <TopBar onToggleSidebar={() => setOpen((o) => !o)} />
        </div>
        <main role="main">{children}</main>
      </div>
    </div>
  );
}
