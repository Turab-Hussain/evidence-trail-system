import type { AmbiguityType, Channel, TrailEntry } from "../types";
import { CHANNEL_LABEL, plural } from "./format";

export interface TrailDisplay {
  title: string;
  detail?: string;
}

/** Backend step names -> plain-language titles. */
const STEP_TITLE: Record<string, string> = {
  ingested: "Message received",
  extracted: "Requirements extracted from the message",
  requirement_created: "Requirement created",
  requirement_merged: "New evidence merged in",
  duplicate_linked: "Repeated message linked",
  ambiguity_checked: "Checked for unclear wording",
  pm_approve: "Approved by project manager",
  pm_edit: "Edited and approved by project manager",
  pm_reject: "Rejected by project manager",
  client_confirmed: "Client confirmed",
  client_changes_requested: "Client asked for changes",
};

const AMBIGUITY_TITLE: Record<AmbiguityType, string> = {
  vague_term: "Unclear wording",
  missing_constraint: "Missing target",
  conflict: "Conflicting values",
};

export function ambiguityTitle(type: AmbiguityType): string {
  return AMBIGUITY_TITLE[type];
}

/** Plain-language title for a backend step name (falls back to the name itself). */
export function stepTitle(step: string): string {
  return STEP_TITLE[step] ?? humanise(step);
}

function humanise(snake: string): string {
  const text = snake.replace(/_/g, " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/** Split ``"step: detail"`` on the first colon. */
function splitSummary(summary: string): [string, string] {
  const index = summary.indexOf(":");
  if (index === -1) return [summary.trim(), ""];
  return [summary.slice(0, index).trim(), summary.slice(index + 1).trim()];
}

/** Turn a backend trail entry into text a project manager can read. */
export function describeTrailEntry(entry: TrailEntry): TrailDisplay {
  switch (entry.kind) {
    case "source": {
      // The quoted words are already shown in "What the client said"; the trail only
      // records that the message arrived, and where from.
      const channel = /^\[([^\]]+)\]/.exec(entry.summary)?.[1] as Channel | undefined;
      return { title: channel && channel in CHANNEL_LABEL ? `${CHANNEL_LABEL[channel]} message received` : "Client message received" };
    }
    case "ambiguity": {
      const [type, explanation] = splitSummary(entry.summary);
      const title = AMBIGUITY_TITLE[type as AmbiguityType] ?? humanise(type);
      return { title, detail: explanation };
    }
    case "version": {
      const [label, changes] = splitSummary(entry.summary);
      return { title: `Saved as version ${label.replace(/^v/, "")}`, detail: changes };
    }
    default: {
      const [step, detail] = splitSummary(entry.summary);
      const title = STEP_TITLE[step] ?? humanise(step);
      if (step === "ambiguity_checked") {
        const found = /(\d+)\s+finding/.exec(detail);
        return { title, detail: found ? `${plural(Number(found[1]), "issue")} found` : undefined };
      }
      if (step === "requirement_merged") {
        return { title, detail: detail ? humanise(detail) : undefined };
      }
      if (step.startsWith("client_")) return { title, detail: detail || undefined };
      return { title };
    }
  }
}
