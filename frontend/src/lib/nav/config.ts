/**
 * Shared navigation configuration.
 *
 * Single source of truth for the primary workspace nav (Dashboard,
 * Documents, Chat). Used by `<Sidebar>` today; later phases can reuse
 * this for breadcrumbs, command palettes, etc.
 *
 * Adding a new top-level destination? Append here — do NOT hard-code
 * the href in any page.
 */

export interface NavItem {
  href: string;
  label: string;
}

export const PRIMARY_NAV: readonly NavItem[] = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/documents", label: "Documents" },
  { href: "/courses", label: "Courses" },
  { href: "/chat", label: "Chat" },
] as const;

/** Used for active-state highlighting: prefix match for nested routes. */
export function isNavItemActive(pathname: string, itemHref: string): boolean {
  return pathname === itemHref || pathname.startsWith(`${itemHref}/`);
}
