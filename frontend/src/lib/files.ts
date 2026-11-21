/** Client-side checks for uploads, so obvious problems are reported before anything is sent. */

export const MAX_FILE_BYTES = 5 * 1024 * 1024;
export const MAX_FILES = 10;
export const ACCEPTED_EXTENSIONS = [".pdf", ".docx", ".txt", ".md", ".eml", ".vtt", ".srt", ".csv"] as const;

export function extensionOf(name: string): string {
  const dot = name.lastIndexOf(".");
  return dot === -1 ? "" : name.slice(dot).toLowerCase();
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(bytes < 10 * 1024 ? 1 : 0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/** The reason a file can't be uploaded, or ``null`` if it looks fine. */
export function fileProblem(file: { name: string; size: number }): string | null {
  if (!(ACCEPTED_EXTENSIONS as readonly string[]).includes(extensionOf(file.name))) {
    return `Unsupported type. Use ${ACCEPTED_EXTENSIONS.join(", ")}.`;
  }
  if (file.size === 0) return "The file is empty.";
  if (file.size > MAX_FILE_BYTES) return `Larger than ${formatBytes(MAX_FILE_BYTES)}.`;
  return null;
}

/**
 * Add newly chosen files to the current list: duplicates (same name and size) are
 * skipped and the total is capped at ``MAX_FILES``. ``skipped`` counts files left out.
 */
export function mergeFiles<T extends { name: string; size: number }>(
  current: T[],
  incoming: T[],
): { files: T[]; skipped: number } {
  const files = [...current];
  let skipped = 0;
  for (const file of incoming) {
    const duplicate = files.some((existing) => existing.name === file.name && existing.size === file.size);
    if (duplicate || files.length >= MAX_FILES) skipped += 1;
    else files.push(file);
  }
  return { files, skipped };
}
