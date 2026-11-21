import type { Project } from "../../types";

interface SidebarProps {
  projects: Project[] | null;
  selectedId: string | null;
  onSelect: (projectId: string) => void;
  onNewProject: () => void;
}

/** The project list on the left of the workspace. */
export function Sidebar({ projects, selectedId, onSelect, onNewProject }: SidebarProps) {
  return (
    <aside className="rail" aria-label="Projects">
      <p className="rail-heading">Projects</p>
      <ul className="project-list">
        {(projects ?? []).map((project) => (
          <li key={project.project_id}>
            <button
              type="button"
              className="project-item"
              aria-current={project.project_id === selectedId}
              onClick={() => onSelect(project.project_id)}
            >
              <strong>{project.name}</strong>
              <span>{project.client}</span>
            </button>
          </li>
        ))}
        {projects?.length === 0 && <li className="rail-heading">None yet</li>}
      </ul>
      <div className="rail-foot">
        <button type="button" className="btn" onClick={onNewProject}>
          New project
        </button>
      </div>
    </aside>
  );
}
