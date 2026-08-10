"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Logo } from "@/components/ui/Logo";
import { cn } from "@/lib/utils/cn";
import { useAuth } from "@/lib/hooks/useAuth";
import type { ReactNode } from "react";
import styles from "./Sidebar.module.css";

interface NavItem {
  href: string;
  label: string;
}

const PRIMARY_ITEMS: NavItem[] = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/documents", label: "Documents" },
  { href: "/chat", label: "Chat" },
];

interface Props {
  open: boolean;
  onClose(): void;
}

export function Sidebar({ open, onClose }: Props): ReactNode {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <>
      {open ? (
        <button
          aria-label="Close navigation"
          className={styles.scrim}
          onClick={onClose}
        />
      ) : null}
      <aside
        className={cn(styles.sidebar, open && styles.sidebarOpen)}
        aria-label="Primary navigation"
      >
        <div className={styles.brand}>
          <Link href="/" onClick={onClose}>
            <Logo />
          </Link>
        </div>

        <nav className={styles.nav} aria-label="Main">
          <div className={styles.section}>Workspace</div>
          {PRIMARY_ITEMS.map((item) => {
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(styles.link, active && styles.linkActive)}
                aria-current={active ? "page" : undefined}
                onClick={onClose}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className={styles.footer}>
          {user ? (
            <>
              <div style={{ fontSize: "var(--text-sm)", color: "var(--fg-secondary)" }}>
                {user.email}
              </div>
              <button
                type="button"
                onClick={logout}
                className={styles.link}
                style={{ background: "transparent", border: "none", cursor: "pointer", width: "100%", textAlign: "left", marginTop: "var(--space-2)" }}
              >
                Sign out
              </button>
            </>
          ) : (
            <Link href="/login" className={styles.link} onClick={onClose}>
              Sign in
            </Link>
          )}
        </div>
      </aside>
    </>
  );
}
