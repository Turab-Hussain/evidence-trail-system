import { describe, expect, it } from "vitest";
import { toWhatsAppPayload } from "../api/client";
import type { AmbiguityFinding } from "../types";
import { formatRelative, plural } from "./format";
import { splitByTerms, vagueTerms } from "./highlight";
import { buildHash, parseHash } from "./useHashRoute";

const finding = (explanation: string, issue_type: AmbiguityFinding["issue_type"] = "vague_term"): AmbiguityFinding => ({
  finding_id: "f",
  requirement_id: "r",
  issue_type,
  explanation,
  clarification_question: "?",
});

describe("highlight", () => {
  it("extracts vague terms from findings only", () => {
    const terms = vagueTerms([
      finding("'premium' is subjective."),
      finding("'Premium' is subjective."),
      finding("Sources give different values for 'second': 3, 5.", "conflict"),
    ]);
    expect(terms).toEqual(["premium"]);
  });

  it("splits text around whole-word, case-insensitive matches", () => {
    expect(splitByTerms("Make it Premium, not premiumish.", ["premium"])).toEqual([
      { text: "Make it ", flagged: false },
      { text: "Premium", flagged: true },
      { text: ", not premiumish.", flagged: false },
    ]);
  });

  it("treats hyphenated words as one word and escapes regex characters", () => {
    expect(splitByTerms("a user-friendly app", ["user-friendly"])[1]).toEqual({
      text: "user-friendly",
      flagged: true,
    });
    // Regex metacharacters in a term are escaped, so they match literally instead of throwing.
    expect(splitByTerms("cost (est.)", ["(est.)"]).some((s) => s.flagged)).toBe(true);
  });

  it("returns the text untouched when there is nothing to flag", () => {
    expect(splitByTerms("hello", [])).toEqual([{ text: "hello", flagged: false }]);
  });
});

describe("routing", () => {
  it("round-trips project and requirement ids", () => {
    const hash = buildHash("proj-1", "req 2");
    expect(parseHash(hash)).toEqual({ page: "project", projectId: "proj-1", requirementId: "req 2" });
  });

  it("handles empty and project-only hashes", () => {
    expect(parseHash("")).toEqual({ page: "dashboard", projectId: null, requirementId: null });
    expect(parseHash("#/p/abc")).toEqual({ page: "project", projectId: "abc", requirementId: null });
    expect(buildHash(null, "x")).toBe("#/dashboard");
  });

  it("recognises the account pages", () => {
    expect(parseHash("#/login").page).toBe("login");
    expect(parseHash("#/signup").page).toBe("signup");
    expect(parseHash("#/dashboard").page).toBe("dashboard");
  });
});

describe("format", () => {
  const now = new Date("2026-11-21T12:00:00Z");
  it("describes recent times relatively", () => {
    expect(formatRelative("2026-11-21T11:59:50Z", now)).toBe("just now");
    expect(formatRelative("2026-11-21T11:30:00Z", now)).toBe("30 min ago");
    expect(formatRelative("2026-11-21T09:00:00Z", now)).toBe("3 h ago");
    expect(formatRelative("2026-11-19T12:00:00Z", now)).toBe("2 d ago");
  });

  it("pluralises", () => {
    expect(plural(1, "requirement")).toBe("1 requirement");
    expect(plural(0, "requirement")).toBe("0 requirements");
  });
});

describe("whatsapp payload", () => {
  it("matches the Cloud API webhook shape the backend parses", () => {
    const payload = toWhatsAppPayload("Need JazzCash", "Sara") as {
      entry: { changes: { value: { messages: { from: string; type: string; text: { body: string } }[] } }[] }[];
    };
    const message = payload.entry[0].changes[0].value.messages[0];
    expect(message).toMatchObject({ from: "Sara", type: "text", text: { body: "Need JazzCash" } });
  });
});
