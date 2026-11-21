import { useState } from "react";
import { plural } from "../../lib/format";
import type { Requirement, ReviewInput } from "../../types";

interface ReviewBarProps {
  requirement: Requirement;
  /** Number of unresolved ambiguity findings, used for a gentle warning. */
  openFindings: number;
  busy: boolean;
  onReview: (input: ReviewInput) => Promise<void>;
}

type Mode = "idle" | "edit" | "reject";

/** Approve, edit-then-approve, or reject. Nothing is final until a person chooses. */
export function ReviewBar({ requirement, openFindings, busy, onReview }: ReviewBarProps) {
  const [mode, setMode] = useState<Mode>("idle");
  const [title, setTitle] = useState(requirement.title);
  const [description, setDescription] = useState(requirement.description);
  const [reason, setReason] = useState("");

  const edited = title.trim() !== requirement.title || description.trim() !== requirement.description;

  return (
    <div className="review-bar">
      {mode === "idle" && (
        <>
          <button type="button" className="btn btn-primary" disabled={busy} onClick={() => onReview({ decision: "approve" })}>
            Approve
          </button>
          <button type="button" className="btn" disabled={busy} onClick={() => setMode("edit")}>
            Edit, then approve
          </button>
          <button type="button" className="btn btn-danger" disabled={busy} onClick={() => setMode("reject")}>
            Reject
          </button>
          {openFindings > 0 && (
            <p className="review-note">
              {plural(openFindings, "unclear point")} still open. You can approve now, or ask the client first and
              edit the wording.
            </p>
          )}
        </>
      )}

      {mode === "edit" && (
        <form
          className="edit-form"
          onSubmit={(event) => {
            event.preventDefault();
            void onReview({
              decision: "edit",
              edited_title: title.trim(),
              edited_description: description.trim(),
            });
          }}
        >
          <label className="field">
            <span>Title</span>
            <input className="input" value={title} onChange={(e) => setTitle(e.target.value)} required />
          </label>
          <label className="field">
            <span>Details</span>
            <textarea
              className="input"
              rows={4}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              required
            />
            <small>Write what will actually be built, with numbers where they matter.</small>
          </label>
          <div className="form-actions">
            <button type="submit" className="btn btn-primary" disabled={busy || !edited || !title.trim() || !description.trim()}>
              Save and approve
            </button>
            <button type="button" className="btn btn-quiet" onClick={() => setMode("idle")}>
              Cancel
            </button>
          </div>
        </form>
      )}

      {mode === "reject" && (
        <form
          className="reject-form"
          onSubmit={(event) => {
            event.preventDefault();
            void onReview({ decision: "reject", note: reason.trim() || undefined });
          }}
        >
          <label className="field">
            <span>Reason for rejecting (optional)</span>
            <input className="input" value={reason} onChange={(e) => setReason(e.target.value)} />
          </label>
          <div className="form-actions">
            <button type="submit" className="btn btn-danger" disabled={busy}>
              Reject requirement
            </button>
            <button type="button" className="btn btn-quiet" onClick={() => setMode("idle")}>
              Cancel
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
