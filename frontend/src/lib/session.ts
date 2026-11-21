/** The signed-in session (token + user), kept in localStorage so a refresh stays signed in. */
import type { User } from "../types";

export interface Session {
  token: string;
  user: User;
}

const KEY = "evidence-trail.session.v1";

export function loadSession(): Session | null {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<Session>;
    if (typeof parsed.token === "string" && parsed.token && parsed.user && typeof parsed.user.name === "string") {
      return { token: parsed.token, user: parsed.user };
    }
  } catch {
    /* corrupt or blocked storage: treat as signed out */
  }
  return null;
}

export function saveSession(session: Session | null): void {
  try {
    if (session) localStorage.setItem(KEY, JSON.stringify(session));
    else localStorage.removeItem(KEY);
  } catch {
    /* storage unavailable: the session lasts until the page closes */
  }
}
