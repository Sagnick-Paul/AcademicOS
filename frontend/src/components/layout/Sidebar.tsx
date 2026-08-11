"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Logo } from "@/components/ui/Logo";
import { cn } from "@/lib/utils/cn";
import { useAuth } from "@/lib/hooks/useAuth";
import { PRIMARY_NAV, isNavItemActive } from "@/lib/nav/config";
import type { ReactNode } from "react";
import styles from "./Sidebar.module.css";

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
          <Link href="/dashboard" onClick={onClose} aria-label="AcademicOS home">
            <Logo />
          </Link>
        </div>

        <nav className={styles.nav} aria-label="Main">
          <div className={styles.section}>Workspace</div>
          {PRIMARY_NAV.map((item) => {
            const active = isNavItemActive(pathname, item.href);
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
            <div className={styles.userBlock}>
              <div className={styles.userName} title={user.full_name}>
                {user.full_name}
              </div>
              <div className={styles.userEmail} title={user.email}>
                {user.email}
              </div>
              <button
                type="button"
                onClick={logout}
                className={cn(styles.link, styles.signOutButton)}
              >
                Sign out
              </button>
            </div>
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
