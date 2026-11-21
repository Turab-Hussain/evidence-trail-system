import { formatDateTime, formatRelative } from "../../lib/format";
import type { User } from "../../types";
import { initials } from "../layout/TopBar";

/** Who is signed in: name, email and account dates. */
export function ProfileCard({ user, onSignOut }: { user: User; onSignOut: () => void }) {
  return (
    <section className="card profile" aria-label="Your account">
      <span className="avatar avatar-large" aria-hidden="true">
        {initials(user.name)}
      </span>
      <h2>{user.name}</h2>
      <p className="profile-email">{user.email}</p>
      <dl className="facts">
        <div>
          <dt>Member since</dt>
          <dd>{new Date(user.created_at).toLocaleDateString(undefined, { dateStyle: "long" })}</dd>
        </div>
        <div>
          <dt>Signed in</dt>
          <dd title={user.last_login_at ? formatDateTime(user.last_login_at) : undefined}>
            {user.last_login_at ? formatRelative(user.last_login_at) : "Just now"}
          </dd>
        </div>
        <div>
          <dt>Account ID</dt>
          <dd className="mono">{user.user_id}</dd>
        </div>
      </dl>
      <button type="button" className="btn btn-block" onClick={onSignOut}>
        Sign out
      </button>
    </section>
  );
}
