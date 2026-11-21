import { useState } from "react";
import { ApiError } from "../../api/client";
import { CHANNEL_LABEL } from "../../lib/format";
import { SAMPLES } from "../../lib/samples";
import type { Channel, UploadResponse } from "../../types";
import { FileUpload } from "../upload/FileUpload";
import { Dialog } from "./Dialog";

export type IngestMode = "paste" | "upload";

interface IngestDialogProps {
  open: boolean;
  projectId: string;
  projectName: string;
  /** Which tab to show first. */
  mode: IngestMode;
  onClose: () => void;
  onSubmitText: (channel: Channel, content: string, sender: string) => Promise<void>;
  onUploaded: (response: UploadResponse) => void;
}

const CHANNELS: Channel[] = ["whatsapp", "email", "meeting_transcript", "document"];

const HINT: Record<Channel, string> = {
  whatsapp: "Paste the message text.",
  email: "Paste the whole email, starting with the Subject line.",
  meeting_transcript: "One line per speaker, for example “[10:02] Sara: We need…”.",
  document: "Separate sections with a blank line.",
};

/** Add client communication to a project: paste text, or upload files. */
export function IngestDialog(props: IngestDialogProps) {
  const { open, onClose } = props;
  return (
    <Dialog open={open} onClose={onClose} labelledBy="ingest-title">
      <IngestBody {...props} />
    </Dialog>
  );
}

function IngestBody({ projectId, projectName, mode, onClose, onSubmitText, onUploaded }: IngestDialogProps) {
  const [tab, setTab] = useState<IngestMode>(mode);

  return (
    <div className="dialog-body">
      <h2 id="ingest-title">Add client messages to {projectName}</h2>
      <div className="tabs" role="tablist" aria-label="How to add messages">
        <button type="button" role="tab" className="filter" aria-selected={tab === "paste"} aria-pressed={tab === "paste"} onClick={() => setTab("paste")}>
          Paste text
        </button>
        <button type="button" role="tab" className="filter" aria-selected={tab === "upload"} aria-pressed={tab === "upload"} onClick={() => setTab("upload")}>
          Upload files
        </button>
      </div>
      {tab === "paste" ? (
        <PasteForm onClose={onClose} onSubmit={onSubmitText} />
      ) : (
        <FileUpload projectId={projectId} onUploaded={onUploaded} onClose={onClose} />
      )}
    </div>
  );
}

function PasteForm({ onClose, onSubmit }: { onClose: () => void; onSubmit: IngestDialogProps["onSubmitText"] }) {
  const [channel, setChannel] = useState<Channel>("whatsapp");
  const [content, setContent] = useState("");
  const [sender, setSender] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await onSubmit(channel, content, sender.trim());
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Couldn't add the messages.");
      setBusy(false);
    }
  }

  return (
    <form className="paste-form" onSubmit={submit}>
      <div className="tabs" role="group" aria-label="Where the message came from">
        {CHANNELS.map((item) => (
          <button key={item} type="button" className="filter" aria-pressed={channel === item} onClick={() => setChannel(item)}>
            {CHANNEL_LABEL[item]}
          </button>
        ))}
      </div>
      <label className="field">
        <span>Message</span>
        <textarea className="input" rows={9} value={content} onChange={(e) => setContent(e.target.value)} required />
        <small>{HINT[channel]}</small>
      </label>
      <label className="field">
        <span>Who sent it? (optional)</span>
        <input className="input" value={sender} onChange={(e) => setSender(e.target.value)} />
      </label>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      <div className="dialog-foot">
        <button
          type="button"
          className="btn btn-quiet"
          onClick={() => {
            setContent(SAMPLES[channel].content);
            setSender(SAMPLES[channel].sender);
          }}
        >
          Fill with an example
        </button>
        <button type="button" className="btn" onClick={onClose}>
          Cancel
        </button>
        <button type="submit" className="btn btn-primary" disabled={busy || !content.trim()}>
          {busy ? "Adding…" : "Add messages"}
        </button>
      </div>
    </form>
  );
}
