import { useState } from "react";
import { ApiError } from "../../api/client";
import { Dialog } from "./Dialog";

interface NewProjectDialogProps {
  open: boolean;
  onClose: () => void;
  onCreate: (name: string, client: string) => Promise<void>;
}

export function NewProjectDialog({ open, onClose, onCreate }: NewProjectDialogProps) {
  return (
    <Dialog open={open} onClose={onClose} labelledBy="project-title">
      <NewProjectForm onClose={onClose} onCreate={onCreate} />
    </Dialog>
  );
}

function NewProjectForm({ onClose, onCreate }: Omit<NewProjectDialogProps, "open">) {
  const [name, setName] = useState("");
  const [client, setClient] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  return (
    <form
      className="dialog-body"
      onSubmit={async (event) => {
        event.preventDefault();
        setBusy(true);
        setError(null);
        try {
          await onCreate(name.trim(), client.trim());
        } catch (caught) {
          setError(caught instanceof ApiError ? caught.message : "Couldn't create the project.");
          setBusy(false);
        }
      }}
    >
      <h2 id="project-title">New project</h2>
      <label className="field">
        <span>Project name</span>
        <input className="input" value={name} onChange={(e) => setName(e.target.value)} required autoFocus />
      </label>
      <label className="field">
        <span>Client</span>
        <input className="input" value={client} onChange={(e) => setClient(e.target.value)} required />
      </label>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      <div className="dialog-foot">
        <button type="button" className="btn" onClick={onClose}>
          Cancel
        </button>
        <button type="submit" className="btn btn-primary" disabled={busy || !name.trim() || !client.trim()}>
          {busy ? "Creating…" : "Create project"}
        </button>
      </div>
    </form>
  );
}
