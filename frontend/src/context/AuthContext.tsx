import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { ApiClient } from "../api/client";
import { loadSettings, saveSettings, type ApiSettings } from "../lib/settings";
import { loadSession, saveSession, type Session } from "../lib/session";
import type { User } from "../types";

interface AuthValue {
  /** The signed-in user, or ``null`` when signed out. */
  user: User | null;
  /** An API client that sends the current token. */
  api: ApiClient;
  settings: ApiSettings;
  /** Set when the server ended the session, so the login page can say why. */
  sessionEnded: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (name: string, email: string, password: string) => Promise<void>;
  logout: () => void;
  updateSettings: (settings: ApiSettings) => void;
}

const AuthContext = createContext<AuthValue | null>(null);

/** Owns the session and the API client; everything below it reads them with ``useAuth``. */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<ApiSettings>(loadSettings);
  const [session, setSession] = useState<Session | null>(loadSession);
  const [sessionEnded, setSessionEnded] = useState(false);

  const endSession = useCallback((expired: boolean) => {
    saveSession(null);
    setSession(null);
    setSessionEnded(expired);
  }, []);

  const api = useMemo(
    () => new ApiClient(settings, session?.token ?? null, () => endSession(true)),
    [settings, session?.token, endSession],
  );

  const start = useCallback((next: Session) => {
    saveSession(next);
    setSession(next);
    setSessionEnded(false);
  }, []);

  const value = useMemo<AuthValue>(
    () => ({
      user: session?.user ?? null,
      api,
      settings,
      sessionEnded,
      login: async (email, password) => start(await api.login(email, password)),
      signup: async (name, email, password) => start(await api.signup(name, email, password)),
      logout: () => endSession(false),
      updateSettings: (next) => {
        saveSettings(next);
        setSettings(next);
      },
    }),
    [session?.user, api, settings, sessionEnded, start, endSession],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside <AuthProvider>");
  return value;
}
