/** Where the backend lives, persisted in the browser. */

export interface ApiSettings {
  /** Base URL of the backend, without a trailing slash. */
  apiUrl: string;
}

const STORAGE_KEY = "evidence-trail.settings.v2";

export const DEFAULT_SETTINGS: ApiSettings = {
  apiUrl: import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000",
};

/** Read the saved address, falling back to the default if missing or corrupt. */
export function loadSettings(): ApiSettings {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_SETTINGS;
    const parsed = JSON.parse(raw) as Partial<ApiSettings>;
    return {
      apiUrl: typeof parsed.apiUrl === "string" && parsed.apiUrl ? parsed.apiUrl : DEFAULT_SETTINGS.apiUrl,
    };
  } catch {
    return DEFAULT_SETTINGS; // storage blocked or JSON corrupt
  }
}

export function saveSettings(settings: ApiSettings): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
  } catch {
    /* storage unavailable (private mode): the address simply lasts for this session */
  }
}

/** Trim whitespace and trailing slashes so URL joining is predictable. */
export function normaliseApiUrl(url: string): string {
  return url.trim().replace(/\/+$/, "");
}
