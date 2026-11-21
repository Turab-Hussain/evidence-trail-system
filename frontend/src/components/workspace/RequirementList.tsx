import { useMemo, useState } from "react";
import { PRIORITY_LABEL, STATUS_LABEL, STATUS_ORDER, plural } from "../../lib/format";
import type { Project, RequirementListItem, RequirementStatus } from "../../types";
import { StatusPill } from "../common/StatusPill";

interface RequirementListProps {
  project: Project;
  items: RequirementListItem[];
  loading: boolean;
  selectedId: string | null;
  onSelect: (requirementId: string) => void;
  onAddMessages: () => void;
  onUploadFiles: () => void;
}

type Filter = "all" | RequirementStatus;

/** The centre pane: project summary, status filters and the list of requirements. */
export function RequirementList({ project, items, loading, selectedId, onSelect, onAddMessages, onUploadFiles }: RequirementListProps) {
  const [filter, setFilter] = useState<Filter>("all");
  const [query, setQuery] = useState("");

  const counts = useMemo(() => {
    const result = Object.fromEntries(STATUS_ORDER.map((s) => [s, 0])) as Record<RequirementStatus, number>;
    for (const item of items) result[item.status] += 1;
    return result;
  }, [items]);

  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return items.filter(
      (item) =>
        (filter === "all" || item.status === filter) &&
        (needle === "" || `${item.title} ${item.description}`.toLowerCase().includes(needle)),
    );
  }, [items, filter, query]);

  return (
    <section className="list-pane" aria-label="Requirements">
      <div className="list-head">
        <div className="list-title">
          <div>
            <h1>{project.name}</h1>
            <p>{project.client}</p>
          </div>
          <div className="list-actions">
            <button type="button" className="btn" onClick={onUploadFiles}>
              Upload files
            </button>
            <button type="button" className="btn btn-primary" onClick={onAddMessages}>
              Add client messages
            </button>
          </div>
        </div>

        {items.length > 0 && (
          <>
            <div className="strip" role="img" aria-label={`${plural(items.length, "requirement")} by status`}>
              {STATUS_ORDER.filter((s) => counts[s] > 0).map((s) => (
                <i key={s} className={`seg-${s}`} style={{ flexGrow: counts[s] }} title={`${STATUS_LABEL[s]}: ${counts[s]}`} />
              ))}
            </div>
            <div className="filters">
              <button type="button" className="filter" aria-pressed={filter === "all"} onClick={() => setFilter("all")}>
                All <b>{items.length}</b>
              </button>
              {STATUS_ORDER.filter((s) => counts[s] > 0).map((s) => (
                <button
                  key={s}
                  type="button"
                  className="filter"
                  aria-pressed={filter === s}
                  onClick={() => setFilter(filter === s ? "all" : s)}
                >
                  {STATUS_LABEL[s]} <b>{counts[s]}</b>
                </button>
              ))}
            </div>
            <input
              className="input search"
              type="search"
              placeholder="Search requirements"
              aria-label="Search requirements"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </>
        )}
      </div>

      {loading && items.length === 0 && <div className="skeleton" aria-hidden="true" />}

      {!loading && items.length === 0 && (
        <div className="empty">
          <h2>No requirements yet</h2>
          <p>
            Paste an email, a WhatsApp message, meeting notes or a document. The system pulls out what the client is
            asking for and flags wording that needs clarifying.
          </p>
          <div className="list-actions">
            <button type="button" className="btn" onClick={onUploadFiles}>
              Upload files
            </button>
            <button type="button" className="btn btn-primary" onClick={onAddMessages}>
              Add client messages
            </button>
          </div>
        </div>
      )}

      {items.length > 0 && visible.length === 0 && (
        <div className="empty">
          <h2>Nothing matches</h2>
          <p>Try a different word, or clear the status filter.</p>
        </div>
      )}

      <ul className="req-list">
        {visible.map((item) => (
          <li key={item.requirement_id}>
            <button
              type="button"
              className="req-row"
              aria-current={item.requirement_id === selectedId}
              onClick={() => onSelect(item.requirement_id)}
            >
              <span className="req-row-title">{item.title}</span>
              <span className="req-row-meta">
                <StatusPill status={item.status} />
                <span>{PRIORITY_LABEL[item.priority]}</span>
                <span>{plural(item.sources.length, "source")}</span>
                {item.open_findings > 0 && <span className="flag">{plural(item.open_findings, "unclear point")}</span>}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
