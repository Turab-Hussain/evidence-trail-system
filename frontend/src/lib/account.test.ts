import { beforeEach, describe, expect, it, vi } from "vitest";
import { initials } from "../components/layout/TopBar";
import { validateSignup } from "../pages/SignupPage";
import { ACCEPTED_EXTENSIONS, MAX_FILES, MAX_FILE_BYTES, fileProblem, formatBytes, mergeFiles } from "./files";
import { loadSession, saveSession } from "./session";
import { loadSettings, normaliseApiUrl } from "./settings";

describe("sign-up validation", () => {
  it("accepts a complete form", () => {
    expect(validateSignup("Sara Khan", "sara@example.com", "longenough", "longenough")).toBeNull();
  });

  it.each([
    ["", "a@b.co", "longenough", "longenough", /name/i],
    ["Sara", "not-an-email", "longenough", "longenough", /email/i],
    ["Sara", "a@b.co", "short", "short", /at least 8/],
    ["Sara", "a@b.co", "longenough", "different1", /match/],
  ])("rejects %j", (name, email, password, confirm, message) => {
    expect(validateSignup(name, email, password, confirm)).toMatch(message);
  });
});

describe("initials", () => {
  it("uses first and last name", () => {
    expect(initials("Sara Khan")).toBe("SK");
    expect(initials("  ali  ")).toBe("A");
    expect(initials("Mary Jane Watson")).toBe("MW");
    expect(initials("")).toBe("?");
  });
});

describe("file checks", () => {
  it("accepts supported types and rejects the rest", () => {
    for (const extension of ACCEPTED_EXTENSIONS) {
      expect(fileProblem({ name: `brief${extension.toUpperCase()}`, size: 100 })).toBeNull();
    }
    expect(fileProblem({ name: "photo.png", size: 100 })).toMatch(/Unsupported/);
    expect(fileProblem({ name: "noextension", size: 100 })).toMatch(/Unsupported/);
  });

  it("rejects empty and oversized files", () => {
    expect(fileProblem({ name: "a.txt", size: 0 })).toMatch(/empty/);
    expect(fileProblem({ name: "a.txt", size: MAX_FILE_BYTES + 1 })).toMatch(/Larger/);
    expect(fileProblem({ name: "a.txt", size: MAX_FILE_BYTES })).toBeNull();
  });

  it("skips duplicates and caps the list", () => {
    const first = { name: "a.txt", size: 1 };
    const merged = mergeFiles([first], [first, { name: "b.txt", size: 2 }]);
    expect(merged.files.map((f) => f.name)).toEqual(["a.txt", "b.txt"]);
    expect(merged.skipped).toBe(1);

    const many = Array.from({ length: MAX_FILES + 3 }, (_, i) => ({ name: `${i}.txt`, size: i + 1 }));
    const capped = mergeFiles([], many);
    expect(capped.files).toHaveLength(MAX_FILES);
    expect(capped.skipped).toBe(3);
  });

  it("formats sizes", () => {
    expect(formatBytes(512)).toBe("512 B");
    expect(formatBytes(2048)).toBe("2.0 KB");
    expect(formatBytes(3 * 1024 * 1024)).toBe("3.0 MB");
  });
});

describe("session and settings storage", () => {
  // Vitest runs in Node, so give the code under test a tiny in-memory localStorage.
  beforeEach(() => {
    const store = new Map<string, string>();
    vi.stubGlobal("localStorage", {
      getItem: (key: string) => store.get(key) ?? null,
      setItem: (key: string, value: string) => void store.set(key, value),
      removeItem: (key: string) => void store.delete(key),
      clear: () => store.clear(),
    });
  });

  it("round-trips a session and ignores corrupt data", () => {
    expect(loadSession()).toBeNull();
    const user = { user_id: "u1", name: "Sara", email: "s@e.co", created_at: "2026-01-01T00:00:00Z", last_login_at: null };
    saveSession({ token: "t", user });
    expect(loadSession()).toEqual({ token: "t", user });
    saveSession(null);
    expect(loadSession()).toBeNull();
    localStorage.setItem("evidence-trail.session.v1", "{broken");
    expect(loadSession()).toBeNull();
    localStorage.setItem("evidence-trail.session.v1", JSON.stringify({ token: "", user }));
    expect(loadSession()).toBeNull();
  });

  it("normalises the API address and falls back to the default", () => {
    expect(normaliseApiUrl(" http://localhost:8000/// ")).toBe("http://localhost:8000");
    localStorage.setItem("evidence-trail.settings.v2", "not json");
    expect(loadSettings().apiUrl).toMatch(/^http/);
  });
});
