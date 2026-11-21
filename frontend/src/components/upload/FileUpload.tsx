import { useId, useRef, useState } from "react";
import { ApiError, type UploadChannel } from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import { ACCEPTED_EXTENSIONS, MAX_FILES, fileProblem, formatBytes, mergeFiles } from "../../lib/files";
import { CHANNEL_LABEL, plural } from "../../lib/format";
import type { UploadResponse } from "../../types";

interface FileUploadProps {
  projectId: string;
  onUploaded: (response: UploadResponse) => void;
  onClose: () => void;
}

const CHANNEL_CHOICES: { value: UploadChannel | ""; label: string }[] = [
  { value: "", label: "Detect from the file type" },
  { value: "document", label: "Document" },
  { value: "email", label: "Email" },
  { value: "transcript", label: "Meeting transcript" },
];

/** Drag-and-drop (or browse) upload of PDF, Word, text, email and caption files. */
export function FileUpload({ projectId, onUploaded, onClose }: FileUploadProps) {
  const { api } = useAuth();
  const inputId = useId();
  const input = useRef<HTMLInputElement>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [channel, setChannel] = useState<UploadChannel | "">("");
  const [dragging, setDragging] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<UploadResponse | null>(null);

  function addFiles(list: FileList | null) {
    if (!list) return;
    const merged = mergeFiles(files, Array.from(list));
    setFiles(merged.files);
    setNote(
      merged.skipped > 0
        ? `${plural(merged.skipped, "file")} skipped: already added, or more than ${MAX_FILES} files.`
        : null,
    );
  }

  const problems = files.map(fileProblem);
  const sendable = files.filter((_, index) => problems[index] === null);

  async function upload() {
    setBusy(true);
    setError(null);
    try {
      const result = await api.uploadFiles(projectId, sendable, channel || null);
      setResponse(result);
      onUploaded(result);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "The upload failed.");
    } finally {
      setBusy(false);
    }
  }

  if (response) {
    return (
      <div className="upload-results">
        <ul>
          {response.results.map((result, index) => (
            <li key={`${result.filename}-${index}`} className={result.ok ? "upload-ok" : "upload-bad"}>
              <strong>{result.filename}</strong>
              {result.ok ? (
                <span>
                  Read as {CHANNEL_LABEL[result.channel ?? "document"].toLowerCase()}:{" "}
                  {plural(result.created_requirements.length, "new requirement")},{" "}
                  {result.updated_requirements.length} merged into existing ones.
                  {result.created_requirements.length + result.updated_requirements.length === 0 &&
                    " No needs found. Statements like “We need…” or “Customers must…” are picked up."}
                </span>
              ) : (
                <span>{result.error}</span>
              )}
            </li>
          ))}
        </ul>
        <div className="dialog-foot">
          <button
            type="button"
            className="btn"
            onClick={() => {
              setResponse(null);
              setFiles([]);
            }}
          >
            Upload more
          </button>
          <button type="button" className="btn btn-primary" onClick={onClose}>
            Done
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="upload">
      <div
        className="dropzone"
        data-dragging={dragging}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          addFiles(event.dataTransfer.files);
        }}
      >
        <p>
          <strong>Drop files here</strong> or
        </p>
        <button type="button" className="btn" onClick={() => input.current?.click()}>
          Choose files
        </button>
        <small>
          {ACCEPTED_EXTENSIONS.join("  ")} · up to {MAX_FILES} files, 5 MB each
        </small>
        <input
          ref={input}
          id={inputId}
          className="visually-hidden"
          type="file"
          multiple
          accept={ACCEPTED_EXTENSIONS.join(",")}
          aria-label="Choose files to upload"
          onChange={(event) => {
            addFiles(event.target.files);
            event.target.value = ""; // allow choosing the same file again after removing it
          }}
        />
      </div>

      {note && <p className="form-notice">{note}</p>}

      {files.length > 0 && (
        <ul className="file-list" aria-label="Files to upload">
          {files.map((file, index) => (
            <li key={`${file.name}-${file.size}`} data-bad={problems[index] !== null}>
              <span className="file-name">{file.name}</span>
              <span className="file-meta">{problems[index] ?? formatBytes(file.size)}</span>
              <button
                type="button"
                className="btn btn-quiet btn-small"
                aria-label={`Remove ${file.name}`}
                onClick={() => setFiles((current) => current.filter((_, i) => i !== index))}
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}

      <label className="field">
        <span>File this under</span>
        <select className="input" value={channel} onChange={(event) => setChannel(event.target.value as UploadChannel | "")}>
          {CHANNEL_CHOICES.map((choice) => (
            <option key={choice.value} value={choice.value}>
              {choice.label}
            </option>
          ))}
        </select>
        <small>Word, PDF and text files are read as documents; .eml as email; .vtt and .srt as meeting transcripts.</small>
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
        <button type="button" className="btn btn-primary" disabled={busy || sendable.length === 0} onClick={upload}>
          {busy ? "Reading files…" : `Upload ${sendable.length > 0 ? plural(sendable.length, "file") : ""}`.trim()}
        </button>
      </div>
    </div>
  );
}
