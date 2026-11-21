import { useState, type ReactNode } from "react";
import { useAuth } from "../../context/AuthContext";
import { SettingsDialog } from "../dialogs/SettingsDialog";
import { Logo } from "./Logo";

interface AuthLayoutProps {
  title: string;
  subtitle: string;
  children: ReactNode;
  /** The "have an account? / new here?" line under the form. */
  footer: ReactNode;
}

/**
 * Shared frame for the sign-in and sign-up pages. The right-hand panel shows the
 * product's one idea (a client's words, the unclear word marked, a trail behind it).
 */
export function AuthLayout({ title, subtitle, children, footer }: AuthLayoutProps) {
  const { settings, updateSettings } = useAuth();
  const [settingsOpen, setSettingsOpen] = useState(false);
  const host = settings.apiUrl.replace(/^https?:\/\//, "");

  return (
    <div className="auth">
      <main className="auth-main">
        <div className="auth-card">
          <div className="brand auth-brand">
            <Logo />
            Evidence Trail
          </div>
          <h1>{title}</h1>
          <p className="auth-sub">{subtitle}</p>
          {children}
          <p className="auth-foot">{footer}</p>
        </div>
        <p className="auth-server">
          Server: {host}{" "}
          <button type="button" className="link-button" onClick={() => setSettingsOpen(true)}>
            Change
          </button>
        </p>
      </main>

      <aside className="auth-aside" aria-hidden="true">
        <figure className="quote auth-quote">
          <blockquote>
            “Please make the homepage look more <mark className="unclear">premium</mark>, and it must load{" "}
            <mark className="unclear">fast</mark>.”
          </blockquote>
          <figcaption>
            <b>Sara</b>, client, on WhatsApp
          </figcaption>
        </figure>
        <ol className="thread auth-thread">
          <li className="k-source">
            <span className="trail-title">WhatsApp message received</span>
          </li>
          <li className="k-ambiguity">
            <span className="trail-title">Unclear wording</span>
            <span className="trail-detail">“premium” and “fast” have no measurable target.</span>
          </li>
          <li className="k-pm_decision">
            <span className="trail-title">Approved by project manager</span>
          </li>
          <li className="k-client_confirmation">
            <span className="trail-title">Client confirmed</span>
          </li>
        </ol>
        <p className="auth-aside-note">Every requirement keeps the path from what the client said to what they approved.</p>
      </aside>

      <SettingsDialog
        open={settingsOpen}
        settings={settings}
        onClose={() => setSettingsOpen(false)}
        onSave={(next) => {
          updateSettings(next);
          setSettingsOpen(false);
        }}
      />
    </div>
  );
}
