import { formatRelative } from "../../lib/format";
import type { ProjectSummary } from "../../types";

interface ProjectsTableProps {
  summaries: ProjectSummary[];
  onOpen: (projectId: string) => void;
  onUpload: (summary: ProjectSummary) => void;
  onNewProject: () => void;
}

/** One row per project, with quick actions. */
export function ProjectsTable({ summaries, onOpen, onUpload, onNewProject }: ProjectsTableProps) {
  return (
    <section className="card" aria-label="Your projects">
      <div className="card-head">
        <h3>Your projects</h3>
        <button type="button" className="btn btn-small" onClick={onNewProject}>
          New project
        </button>
      </div>
      {summaries.length === 0 ? (
        <div className="empty empty-inline">
          <h2>No projects yet</h2>
          <p>Create a project for each client, then add their messages or upload their documents.</p>
          <button type="button" className="btn btn-primary" onClick={onNewProject}>
            Create your first project
          </button>
        </div>
      ) : (
        <div className="table-scroll">
          <table className="table">
            <thead>
              <tr>
                <th scope="col">Project</th>
                <th scope="col" className="num">Messages</th>
                <th scope="col" className="num">Requirements</th>
                <th scope="col" className="num">To review</th>
                <th scope="col" className="num">Confirmed</th>
                <th scope="col">Last activity</th>
                <th scope="col">
                  <span className="visually-hidden">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {summaries.map((summary) => (
                <tr key={summary.project.project_id}>
                  <th scope="row">
                    <button type="button" className="link-button strong" onClick={() => onOpen(summary.project.project_id)}>
                      {summary.project.name}
                    </button>
                    <span className="muted">{summary.project.client}</span>
                  </th>
                  <td className="num">{summary.sources}</td>
                  <td className="num">{summary.requirements}</td>
                  <td className="num">{summary.by_status.pending_approval ?? 0}</td>
                  <td className="num">{summary.by_status.confirmed ?? 0}</td>
                  <td>{summary.last_activity ? formatRelative(summary.last_activity) : "No activity"}</td>
                  <td className="row-actions">
                    <button type="button" className="btn btn-small" onClick={() => onUpload(summary)}>
                      Add files
                    </button>
                    <button type="button" className="btn btn-small btn-primary" onClick={() => onOpen(summary.project.project_id)}>
                      Open
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
