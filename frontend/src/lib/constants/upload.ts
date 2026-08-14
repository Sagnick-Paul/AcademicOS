/**
 * Client-side hints that mirror the backend's allowed upload types.
 *
 * **The backend is the source of truth.** These constants exist only to:
 *
 *  - Surface the supported types in `<input accept="…">` and copy.
 *  - Give the upload button a reasonable filter for the file picker.
 *  - Provide a friendly label for a user-rejected file before it ever
 *    leaves the browser.
 *
 * The backend re-validates extension + Content-Type + magic bytes and
 * returns 415 if the file is unsupported. We deliberately do not
 * duplicate magic-byte checks here — it would be a thin, fragile
 * copy of the server logic.
 *
 * Kept in sync with `backend/app/storage/types.py`:
 *   SUPPORTED_FILE_TYPES = {"pdf", "ppt", "pptx", "png", "jpg", "jpeg"}
 */
export const ACCEPTED_FILE_EXTENSIONS: readonly string[] = [
  ".pdf",
  ".ppt",
  ".pptx",
  ".png",
  ".jpg",
  ".jpeg",
];

/** Comma-separated string suitable for `<input type="file" accept="…">`. */
export const ACCEPT_ATTRIBUTE: string = ACCEPTED_FILE_EXTENSIONS.join(",");

/** Human-readable list of supported formats for the upload card copy. */
export const SUPPORTED_FORMATS_LABEL: string =
  "PDF, PowerPoint (PPTX/PPT), or image (PNG, JPG)";

/**
 * Friendly name for the canonical file type stored by the backend.
 * Falls back to the raw type when it isn't in the friendly map so we
 * never invent a label.
 */
const FRIENDLY_TYPE_LABEL: Record<string, string> = {
  pdf: "PDF",
  ppt: "PowerPoint",
  pptx: "PowerPoint",
  png: "PNG image",
  jpg: "JPEG image",
  jpeg: "JPEG image",
};

export function fileTypeLabel(fileType: string): string {
  return FRIENDLY_TYPE_LABEL[fileType.toLowerCase()] ?? fileType.toUpperCase();
}