import { useState } from "react";
import { ApiError, type ApiClient } from "../../api/client";
import { copyText } from "../../lib/clipboard";
import type { ClientResponse, Requirement } from "../../types";

interface ConfirmationBoxProps {
  api: ApiClient;
  requirement: Requirement;
  busy: boolean;
  onRecord: (response: ClientResponse, note: string) => Promise<void>;
  notify: (message: string, kind?: "info" | "error") => void;
}

/** Draft the message for the client, then record what they answered. */
export function ConfirmationBox({ api, requirement, busy, onRecord, notify }: ConfirmationBoxProps) {
  const [draft, setDraft] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [note, setNote] = useState("");

  if (requirement.status === "confirmed") {
    return <p className="confirm-done">The client confirmed this requirement.</p>;
  }
  if (requirement.status === "changes_requested") {
    return (
      <p className="review-note">
        The client asked for changes. Edit the requirement above and approve it again, then send a new confirmation.
      </p>
    );
  }

  async function loadDraft() {
    setLoading(true);
    try {
      setDraft(await api.getConfirmationDraft(requirement.requirement_id));
    } catch (error) {
      notify(error instanceof ApiError ? error.message : "Couldn't write the message.", "error");
    } finally {
      setLoading(false);
    }
  }

  async function copy() {
    if (draft === null) return;
    notify((await copyText(draft)) ? "Message copied" : "Couldn't copy. Select the text and copy it manually.");
  }

  if (draft === null) {
    return (
      <div>
        <button type="button" className="btn" onClick={loadDraft} disabled={loading}>
          {loading ? "Writing…" : "Write message for the client"}
        </button>
      </div>
    );
  }

  return (
    <div className="section">
      <pre className="draft">{draft}</pre>
      <div className="form-actions">
        <button type="button" className="btn btn-small" onClick={copy}>
          Copy message
        </button>
      </div>
      <label className="field">
        <span>What did the client reply? (optional)</span>
        <input className="input" value={note} onChange={(e) => setNote(e.target.value)} />
      </label>
      <div className="form-actions">
        <button type="button" className="btn btn-primary" disabled={busy} onClick={() => onRecord("confirmed", note)}>
          Client confirmed
        </button>
        <button type="button" className="btn" disabled={busy} onClick={() => onRecord("changes_requested", note)}>
          Client asked for changes
        </button>
      </div>
    </div>
  );
}
