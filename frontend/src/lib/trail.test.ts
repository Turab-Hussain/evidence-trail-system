import { describe, expect, it } from "vitest";
import type { TrailEntry } from "../types";
import { describeTrailEntry } from "./trail";

const entry = (kind: TrailEntry["kind"], summary: string): TrailEntry => ({
  timestamp: "2026-11-21T10:00:00Z",
  kind,
  actor: "system",
  summary,
  reference: null,
});

describe("describeTrailEntry", () => {
  it("names the channel a source message arrived on", () => {
    expect(describeTrailEntry(entry("source", "[whatsapp] Make it premium"))).toEqual({
      title: "WhatsApp message received",
    });
    expect(describeTrailEntry(entry("source", "[fax] x")).title).toBe("Client message received");
  });

  it("names ambiguity types in plain language", () => {
    expect(describeTrailEntry(entry("ambiguity", "vague_term: 'premium' is subjective."))).toEqual({
      title: "Unclear wording",
      detail: "'premium' is subjective.",
    });
  });

  it("explains pipeline steps and hides internal detail", () => {
    expect(describeTrailEntry(entry("ai_step", "extracted: requirement_extraction_agent")).title).toBe(
      "Requirements extracted from the message",
    );
    expect(describeTrailEntry(entry("ai_step", "extracted: requirement_extraction_agent")).detail).toBeUndefined();
    expect(describeTrailEntry(entry("ai_step", "ambiguity_checked: 2 finding(s)")).detail).toBe("2 issues found");
    expect(describeTrailEntry(entry("ai_step", "requirement_merged: now version 2")).detail).toBe("Now version 2");
  });

  it("labels versions and decisions", () => {
    expect(describeTrailEntry(entry("version", "v3: Edited and approved by PM"))).toEqual({
      title: "Saved as version 3",
      detail: "Edited and approved by PM",
    });
    expect(describeTrailEntry(entry("pm_decision", "pm_approve: Approved by PM")).title).toBe(
      "Approved by project manager",
    );
  });

  it("falls back to a readable title for unknown steps", () => {
    expect(describeTrailEntry(entry("other", "some_new_step")).title).toBe("Some new step");
  });
});
