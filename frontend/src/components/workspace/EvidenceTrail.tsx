import { formatDateTime, formatRelative } from "../../lib/format";
import { describeTrailEntry } from "../../lib/trail";
import type { EvidenceTrail as Trail } from "../../types";

interface EvidenceTrailProps {
  trail: Trail;
}

/**
 * The requirement's whole journey as one continuous thread: the client's words,
 * each AI step, the project manager's decision, the client's answer, and every version.
 */
export function EvidenceTrail({ trail }: EvidenceTrailProps) {
  return (
    <>
      {!trail.complete && (
        <p className="trail-missing">Evidence is incomplete: {trail.missing.join("; ")}.</p>
      )}
      <ol className="thread">
        {trail.entries.map((entry, index) => {
          const shown = describeTrailEntry(entry);
          return (
            <li key={`${entry.reference ?? "entry"}-${index}`} className={`k-${entry.kind}`}>
              <p className="trail-title">{shown.title}</p>
              {shown.detail && <p className="trail-detail">{shown.detail}</p>}
              <p className="trail-meta" title={formatDateTime(entry.timestamp)}>
                {entry.actor} &nbsp; {formatRelative(entry.timestamp)}
              </p>
            </li>
          );
        })}
      </ol>
    </>
  );
}
