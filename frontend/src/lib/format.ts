import type { Channel, Priority, RequirementStatus } from "../types";

/** Plain-language labels, written for project managers rather than the data model. */
export const STATUS_LABEL: Record<RequirementStatus, string> = {
  pending_approval: "Needs review",
  approved: "Approved",
  confirmed: "Confirmed by client",
  changes_requested: "Client wants changes",
  rejected: "Rejected",
};

export const CHANNEL_LABEL: Record<Channel, string> = {
  email: "Email",
  whatsapp: "WhatsApp",
  meeting_transcript: "Meeting transcript",
  document: "Document",
};

export const PRIORITY_LABEL: Record<Priority, string> = {
  high: "High priority",
  medium: "Medium priority",
  low: "Low priority",
};

/** Display order for status filters: the work that needs a person comes first. */
export const STATUS_ORDER: RequirementStatus[] = [
  "pending_approval",
  "changes_requested",
  "approved",
  "confirmed",
  "rejected",
];

export function formatConfidence(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function formatDateTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

/** "just now", "5 min ago", "3 h ago", "2 d ago", then a short date. */
export function formatRelative(iso: string, now: Date = new Date()): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  const seconds = Math.round((now.getTime() - date.getTime()) / 1000);
  if (seconds < 45) return "just now";
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  const days = Math.round(hours / 24);
  if (days < 7) return `${days} d ago`;
  return date.toLocaleDateString(undefined, { dateStyle: "medium" });
}

/** Singular/plural helper: ``plural(2, "requirement")`` -> ``"2 requirements"``. */
export function plural(count: number, noun: string): string {
  return `${count} ${noun}${count === 1 ? "" : "s"}`;
}
