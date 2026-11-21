import { useEffect, useRef, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import type { Page } from "../../lib/useHashRoute";
import { SettingsDialog } from "../dialogs/SettingsDialog";
import { Logo } from "./Logo";

interface TopBarProps {
  page: Page;
  onNavigate: (page: "dashboard" | "projects") => void;
}

/** First letter(s) of a name, for the avatar. */
export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  const first = parts[0][0];
  const last = parts.length > 1 ? parts[parts.length - 1][0] : "";
  return (first + last).toUpperCase();
}

/** Brand, main navigation and the account menu. */
export function TopBar({ page, onNavigate }: TopBarProps) {
  const { user, logout, settings, updateSettings } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!menuOpen) return;
    const close = (event: MouseEvent | KeyboardEvent) => {
      if (event instanceof KeyboardEvent) {
        if (event.key === "Escape") setMenuOpen(false);
      } else if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", close);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", close);
    };
  }, [menuOpen]);

  const inProjects = page === "projects" || page === "project";

  return (
    <header className="topbar">
      <button type="button" className="brand brand-button" onClick={() => onNavigate("dashboard")}>
        <Logo />
        Evidence Trail
      </button>
      <nav className="topnav" aria-label="Main">
        <button type="button" aria-current={page === "dashboard" ? "page" : undefined} onClick={() => onNavigate("dashboard")}>
          Dashboard
        </button>
        <button type="button" aria-current={inProjects ? "page" : undefined} onClick={() => onNavigate("projects")}>
          Projects
        </button>
      </nav>

      <div className="account" ref={menuRef}>
        <button
          type="button"
          className="account-button"
          aria-haspopup="menu"
          aria-expanded={menuOpen}
          onClick={() => setMenuOpen((open) => !open)}
        >
          <span className="avatar" aria-hidden="true">
            {initials(user?.name ?? "")}
          </span>
          <span className="account-name">{user?.name}</span>
        </button>
        {menuOpen && (
          <div className="menu" role="menu">
            <div className="menu-head">
              <strong>{user?.name}</strong>
              <span>{user?.email}</span>
            </div>
            <button
              type="button"
              role="menuitem"
              onClick={() => {
                setMenuOpen(false);
                setSettingsOpen(true);
              }}
            >
              Server settings
            </button>
            <button type="button" role="menuitem" onClick={logout}>
              Sign out
            </button>
          </div>
        )}
      </div>

      <SettingsDialog
        open={settingsOpen}
        settings={settings}
        onClose={() => setSettingsOpen(false)}
        onSave={(next) => {
          updateSettings(next);
          setSettingsOpen(false);
        }}
      />
    </header>
  );
}
