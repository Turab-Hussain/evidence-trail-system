import { useState } from "react";
import { normaliseApiUrl, type ApiSettings } from "../../lib/settings";
import { Dialog } from "./Dialog";

interface SettingsDialogProps {
  open: boolean;
  settings: ApiSettings;
  onClose: () => void;
  onSave: (settings: ApiSettings) => void;
}

export function SettingsDialog({ open, settings, onClose, onSave }: SettingsDialogProps) {
  return (
    <Dialog open={open} onClose={onClose} labelledBy="settings-title">
      <SettingsForm settings={settings} onClose={onClose} onSave={onSave} />
    </Dialog>
  );
}

function SettingsForm({ settings, onClose, onSave }: Omit<SettingsDialogProps, "open">) {
  const [apiUrl, setApiUrl] = useState(settings.apiUrl);

  return (
    <form
      className="dialog-body"
      onSubmit={(event) => {
        event.preventDefault();
        onSave({ apiUrl: normaliseApiUrl(apiUrl) });
      }}
    >
      <h2 id="settings-title">Server settings</h2>
      <label className="field">
        <span>API address</span>
        <input className="input" type="url" value={apiUrl} onChange={(e) => setApiUrl(e.target.value)} required />
        <small>Where the backend is running. The default is http://127.0.0.1:8000.</small>
      </label>
      <div className="dialog-foot">
        <button type="button" className="btn" onClick={onClose}>
          Cancel
        </button>
        <button type="submit" className="btn btn-primary">
          Save
        </button>
      </div>
    </form>
  );
}
