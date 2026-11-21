import { useState } from "react";
import { ApiError } from "../api/client";
import { PasswordField } from "../components/auth/PasswordField";
import { AuthLayout } from "../components/layout/AuthLayout";
import { useAuth } from "../context/AuthContext";

export const MIN_PASSWORD_LENGTH = 8;

/** Returns the first problem with the sign-up form, or ``null`` when it can be submitted. */
export function validateSignup(name: string, email: string, password: string, confirm: string): string | null {
  if (!name.trim()) return "Please enter your name.";
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email.trim())) return "Please enter a valid email address.";
  if (password.length < MIN_PASSWORD_LENGTH) return `Password must be at least ${MIN_PASSWORD_LENGTH} characters.`;
  if (password !== confirm) return "The two passwords don't match.";
  return null;
}

export function SignupPage({ onSignedIn, onLogin }: { onSignedIn: () => void; onLogin: () => void }) {
  const { signup } = useAuth();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    const problem = validateSignup(name, email, password, confirm);
    if (problem) {
      setError(problem);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await signup(name.trim(), email.trim(), password);
      onSignedIn();
    } catch (caught) {
      setError(
        caught instanceof ApiError && caught.isUnreachable
          ? `${caught.message} Start the backend, or change the server address below.`
          : caught instanceof ApiError
            ? caught.message
            : "Couldn't create the account.",
      );
      setBusy(false);
    }
  }

  return (
    <AuthLayout
      title="Create your account"
      subtitle="Your projects and client messages stay private to you."
      footer={
        <>
          Already registered?{" "}
          <button type="button" className="link-button" onClick={onLogin}>
            Sign in
          </button>
        </>
      }
    >
      <form className="auth-form" onSubmit={submit} noValidate>
        <label className="field">
          <span>Your name</span>
          <input className="input" autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} required autoFocus />
          <small>Shown on the dashboard and recorded next to every approval you make.</small>
        </label>
        <label className="field">
          <span>Email</span>
          <input className="input" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </label>
        <PasswordField
          label="Password"
          value={password}
          onChange={setPassword}
          autoComplete="new-password"
          hint={`At least ${MIN_PASSWORD_LENGTH} characters.`}
        />
        <PasswordField label="Confirm password" value={confirm} onChange={setConfirm} autoComplete="new-password" />
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        <button type="submit" className="btn btn-primary btn-wide" disabled={busy}>
          {busy ? "Creating account…" : "Create account"}
        </button>
      </form>
    </AuthLayout>
  );
}
