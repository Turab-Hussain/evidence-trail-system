import type { AmbiguityFinding } from "../types";

export interface Segment {
  text: string;
  flagged: boolean;
}

/** The quoted word in a finding such as ``'premium' is subjective...``. */
const QUOTED_TERM = /^'([^']+)'/;

/** Words the ambiguity check flagged as vague, lower-cased and de-duplicated. */
export function vagueTerms(findings: AmbiguityFinding[]): string[] {
  const terms = new Set<string>();
  for (const finding of findings) {
    if (finding.issue_type !== "vague_term") continue;
    const match = QUOTED_TERM.exec(finding.explanation);
    if (match) terms.add(match[1].toLowerCase());
  }
  return [...terms];
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/**
 * Split ``text`` into segments, marking the ones that match a flagged term.
 * Matching is case-insensitive and whole-word (hyphenated words count as one word).
 */
export function splitByTerms(text: string, terms: string[]): Segment[] {
  if (terms.length === 0 || text === "") return [{ text, flagged: false }];

  const pattern = new RegExp(`(?<![\\w-])(${terms.map(escapeRegExp).join("|")})(?![\\w-])`, "gi");
  const segments: Segment[] = [];
  let cursor = 0;
  for (const match of text.matchAll(pattern)) {
    const start = match.index ?? 0;
    if (start > cursor) segments.push({ text: text.slice(cursor, start), flagged: false });
    segments.push({ text: match[0], flagged: true });
    cursor = start + match[0].length;
  }
  if (cursor < text.length) segments.push({ text: text.slice(cursor), flagged: false });
  return segments;
}
