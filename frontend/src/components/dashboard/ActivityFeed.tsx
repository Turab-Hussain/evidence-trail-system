import { formatDateTime, formatRelative } from "../../lib/format";
import { stepTitle } from "../../lib/trail";
import type { ActivityItem } from "../../types";

/** The newest steps recorded in the evidence trail across all projects. */
export function ActivityFeed({
  items,
  onOpen,
}: {
  items: ActivityItem[];
  onOpen: (projectId: string, requirementId: string | null) => void;
}) {
  return (
    <section className="card" aria-label="Recent activity">
      <h3>Recent activity</h3>
      {items.length === 0 ? (
        <p className="muted">Activity appears here as you add messages and review requirements.</p>
      ) : (
        <ol className="feed">
          {items.map((item, index) => (
            <li key={`${item.timestamp}-${index}`}>
              <button type="button" className="feed-item" onClick={() => onOpen(item.project_id, item.requirement_id)}>
                <span className="feed-title">{stepTitle(item.step)}</span>
                <span className="feed-sub">
                  {item.requirement_title ? `${item.requirement_title} · ` : ""}
                  {item.project_name}
                </span>
              </button>
              <time dateTime={item.timestamp} title={formatDateTime(item.timestamp)}>
                {formatRelative(item.timestamp)}
              </time>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
