import { useState } from "react";
import { ApiError, type ApiClient } from "../../api/client";
import { copyText } from "../../lib/clipboard";
import { PRIORITY_LABEL, formatConfidence, formatRelative, formatDateTime, CHANNEL_LABEL, plural } from "../../lib/format";
import { splitByTerms, vagueTerms } from "../../lib/highlight";
import { ambiguityTitle } from "../../lib/trail";
import { useResource } from "../../lib/useResource";
import type { ClientResponse, ReviewInput } from "../../types";
import { ConfirmationBox } from "./ConfirmationBox";
import { EvidenceTrail } from "./EvidenceTrail";
import { ReviewBar } from "./ReviewBar";
import { StatusPill } from "../common/StatusPill";

interface RequirementPanelProps {
  api: ApiClient;
  requirementId: string;
  /** Name recorded on review decisions. */
  /** Called after any change so the list can refresh. */
  onChanged: () => void;
  onBack: () => void;
  notify: (message: string, kind?: "info" | "error") => void;
}

/** Right-hand pane: one requirement with its evidence, questions, decision and trail. */
export function RequirementPanel({ api, requirementId, onChanged, onBack, notify }: RequirementPanelProps) {
  const detail = useResource(() => api.getRequirement(requirementId), [api, requirementId]);
  const trail = useResource(() => api.getTrail(requirementId), [api, requirementId]);
  const [busy, setBusy] = useState(false);

  const refresh = () => {
    detail.reload();
    trail.reload();
    onChanged();
  };

  /** Run a change, report the outcome, and refresh everything that shows it. */
  async function perform(action: () => Promise<unknown>, successMessage: string) {
    setBusy(true);
    try {
      await action();
      notify(successMessage);
      refresh();
    } catch (error) {
      notify(error instanceof ApiError ? error.message : "Something went wrong.", "error");
    } finally {
      setBusy(false);
    }
  }

  if (detail.error && !detail.data) {
    return (
      <div className="detail">
        <button type="button" className="btn btn-quiet back" onClick={onBack}>
          Back to list
        </button>
        <p className="banner">{detail.error.message}</p>
      </div>
    );
  }
  if (!detail.data) return <div className="skeleton" aria-hidden="true" />;

  const { requirement, findings, sources } = detail.data;
  const unclearTerms = vagueTerms(findings);
  const reviewable = requirement.status === "pending_approval" || requirement.status === "changes_requested";
  const showConfirmation = ["approved", "confirmed", "changes_requested"].includes(requirement.status);
  const sourceById = new Map(sources.map((source) => [source.source_id, source]));

  async function review(input: ReviewInput) {
    const messages = { approve: "Approved", edit: "Edited and approved", reject: "Rejected" } as const;
    await perform(() => api.review(requirementId, input), messages[input.decision]);
  }

  async function record(response: ClientResponse, note: string) {
    await perform(
      () => api.recordConfirmation(requirementId, response, note),
      response === "confirmed" ? "Marked as confirmed" : "Marked as changes requested",
    );
  }

  async function copyQuestions() {
    const text = findings.map((f) => `- ${f.clarification_question}`).join("\n");
    notify((await copyText(text)) ? "Questions copied" : "Couldn't copy. Select the text and copy it manually.");
  }

  return (
    <article className="detail" aria-label={requirement.title}>
      <button type="button" className="btn btn-quiet back" onClick={onBack}>
        Back to list
      </button>

      <header className="detail-head">
        <div>
          <StatusPill status={requirement.status} />
        </div>
        <h2>{requirement.title}</h2>
        <p className="detail-desc">{requirement.description}</p>
        <p className="detail-meta">
          <span>{requirement.type === "functional" ? "Feature" : "Quality target"}</span>
          <span>{PRIORITY_LABEL[requirement.priority]}</span>
          <span title="How sure the system is that this reads the client correctly">
            {formatConfidence(requirement.confidence)} confidence
          </span>
          <span>Version {requirement.version}</span>
        </p>
      </header>

      {reviewable && (
        <ReviewBar key={requirement.version} requirement={requirement} openFindings={findings.length} busy={busy} onReview={review} />
      )}

      <section className="section">
        <h3>
          What the client said <small>{plural(requirement.sources.length, "message")}</small>
        </h3>
        {requirement.sources.map((ref, index) => {
          const message = sourceById.get(ref.source_id);
          return (
            <figure className="quote" key={`${ref.source_id}-${index}`}>
              <blockquote>
                {splitByTerms(ref.snippet, unclearTerms).map((segment, i) =>
                  segment.flagged ? (
                    <mark key={i} className="unclear">
                      {segment.text}
                    </mark>
                  ) : (
                    <span key={i}>{segment.text}</span>
                  ),
                )}
              </blockquote>
              {message && (
                <figcaption>
                  <b>{CHANNEL_LABEL[message.channel]}</b>
                  {message.sender ? ` from ${message.sender}` : ""},{" "}
                  <time dateTime={message.timestamp} title={formatDateTime(message.timestamp)}>
                    {formatRelative(message.timestamp)}
                  </time>
                </figcaption>
              )}
              {message && message.content.trim() !== ref.snippet.trim() && (
                <details className="full-message">
                  <summary>Show full message</summary>
                  <pre>{message.content}</pre>
                </details>
              )}
            </figure>
          );
        })}
      </section>

      {findings.length > 0 && (
        <section className="section">
          <h3>
            Questions to ask the client
            <button type="button" className="btn btn-small btn-quiet" onClick={copyQuestions}>
              Copy questions
            </button>
          </h3>
          {findings.map((finding) => (
            <div className="finding" key={finding.finding_id}>
              <p>
                <b>{ambiguityTitle(finding.issue_type)}.</b> {finding.explanation}
              </p>
              <p>{finding.clarification_question}</p>
            </div>
          ))}
        </section>
      )}

      {showConfirmation && (
        <section className="section">
          <h3>Client confirmation</h3>
          <ConfirmationBox
            key={`${requirement.status}-${requirement.version}`}
            api={api}
            requirement={requirement}
            busy={busy}
            onRecord={record}
            notify={notify}
          />
        </section>
      )}

      <section className="section">
        <h3>Evidence trail</h3>
        {trail.data ? (
          <EvidenceTrail trail={trail.data} />
        ) : trail.error ? (
          <p className="banner">{trail.error.message}</p>
        ) : (
          <div className="skeleton" aria-hidden="true" />
        )}
      </section>
    </article>
  );
}
