/**
 * Small UI formatters for document cards. No logic; just shape
 * presentation, kept here so the cards stay tidy and the rules are
 * easy to find and tweak in one place.
 */

/** Format a byte count as a human-readable size (e.g. "1.4 MB"). */
export function formatFileSize(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes < 0) return "—";
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB", "TB"];
  let value = bytes / 1024;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  const formatted = value < 10 ? value.toFixed(1) : value.toFixed(0);
  return `${formatted} ${units[unitIndex]}`;
}

/**
 * Format an ISO timestamp as a short, locale-aware date string.
 *
 * Falls back to the raw string when the input is invalid rather than
 * throwing — the cards must render even if a backend row has a bad
 * timestamp.
 */
export function formatDate(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}