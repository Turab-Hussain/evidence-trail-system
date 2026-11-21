import { useState } from "react";
import { ApiError } from "../api/client";
import { PasswordField } from "../components/auth/PasswordField";
import { AuthLayout } from "../components/layout/AuthLayout";
import { useAuth } from "../context/AuthContext";

export function LoginPage({ onSignedIn, onSignup }: { onSignedIn: () => void; onSignup: () => void }) {
  const { login, sessionEnded } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email, password);
      onSignedIn();
    } catch (caught) {
      setError(
        caught instanceof ApiError && caught.isUnreachable
          ? `${caught.message} Start the backend, or change the server address below.`
          : caught instanceof ApiError
            ? caught.message
            : "Couldn't sign in.",
      );
      setBusy(false);
    }
  }

  return (
    <AuthLayout
      title="Sign in"
      subtitle="Pick up where your projects left off."
      footer={
        <>
          New here?{" "}
          <button type="button" className="link-button" onClick={onSignup}>
            Create an account
          </button>
        </>
      }
    >
      <form className="auth-form" onSubmit={submit}>
        {sessionEnded && !error && (
          <p className="form-notice" role="status">
            Your session ended. Sign in again to continue.
          </p>
        )}
        <label className="field">
          <span>Email</span>
          <input
            className="input"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoFocus
          />
        </label>
        <PasswordField label="Password" value={password} onChange={setPassword} autoComplete="current-password" />
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        <button type="submit" className="btn btn-primary btn-wide" disabled={busy || !email || !password}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </AuthLayout>
  );
}
