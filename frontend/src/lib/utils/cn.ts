/**
 * Tiny className merger.
 *
 * Not clsx — keeps the dependency surface at zero. Filters falsy values so
 * callers can write `cn("base", isActive && "active", className)`.
 */
export type ClassValue = string | number | false | null | undefined;

export function cn(...values: ClassValue[]): string {
  return values.filter(Boolean).join(" ");
}
