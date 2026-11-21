import { useState } from "react";
import { IngestDialog, type IngestMode } from "../components/dialogs/IngestDialog";
import { NewProjectDialog } from "../components/dialogs/NewProjectDialog";
import { RequirementList } from "../components/workspace/RequirementList";
import { RequirementPanel } from "../components/workspace/RequirementPanel";
import { Sidebar } from "../components/workspace/Sidebar";
import { useAuth } from "../context/AuthContext";
import { useNotify } from "../context/ToastContext";
import { plural } from "../lib/format";
import { useResource } from "../lib/useResource";
import type { Route } from "../lib/useHashRoute";
import type { Channel, RequirementListItem, UploadResponse } from "../types";

const NO_REQUIREMENTS: RequirementListItem[] = [];

interface WorkspacePageProps {
  route: Route;
  onOpenProject: (projectId: string, requirementId?: string | null) => void;
}

/** Projects on the left, the selected project's requirements in the middle, one requirement on the right. */
export function WorkspacePage({ route, onOpenProject }: WorkspacePageProps) {
  const { api } = useAuth();
  const notify = useNotify();
  const [dialog, setDialog] = useState<"project" | IngestMode | null>(null);

  const projects = useResource(() => api.listProjects(), [api]);
  const requirements = useResource(
    () => (route.projectId ? api.listRequirements(route.projectId) : Promise.resolve(NO_REQUIREMENTS)),
    [api, route.projectId],
  );

  const project = projects.data?.find((item) => item.project_id === route.projectId) ?? null;
  // Ignore rows from a previously selected project while the new list loads.
  const items = (requirements.data ?? NO_REQUIREMENTS).filter((item) => item.project_id === route.projectId);

  async function addMessages(channel: Channel, content: string, sender: string) {
    if (!project) return;
    const result = await api.ingest(project.project_id, channel, content, sender);
    setDialog(null);
    requirements.reload();

    const created = result.created_requirements.length;
    const merged = result.updated_requirements.length;
    if (created + merged === 0) {
      notify("No requirements found. Try wording it as a need, such as “We need…”.");
    } else {
      const failed = result.failed_sources.length;
      notify(
        `Added ${plural(result.source_ids.length, "message")}: ${created} new, ${merged} updated.` +
          (failed ? ` ${plural(failed, "message")} could not be processed.` : ""),
        failed ? "error" : "info",
      );
      onOpenProject(project.project_id, result.created_requirements[0] ?? result.updated_requirements[0]);
    }
  }

  function uploaded(response: UploadResponse) {
    requirements.reload();
    const created = response.results.reduce((sum, r) => sum + r.created_requirements.length, 0);
    const ok = response.results.filter((r) => r.ok).length;
    if (ok > 0) notify(`Read ${plural(ok, "file")}: ${plural(created, "new requirement")}.`);
  }

  async function createProject(name: string, client: string) {
    const created = await api.createProject(name, client);
    setDialog(null);
    projects.reload();
    onOpenProject(created.project_id);
    notify(`Created ${created.name}`);
  }

  return (
    <div className="workspace" data-detail={route.requirementId !== null ? "open" : "closed"}>
      <Sidebar
        projects={projects.data}
        selectedId={route.projectId}
        onSelect={(id) => onOpenProject(id)}
        onNewProject={() => setDialog("project")}
      />

      {project ? (
        <RequirementList
          project={project}
          items={items}
          loading={requirements.loading}
          selectedId={route.requirementId}
          onSelect={(id) => onOpenProject(project.project_id, id)}
          onAddMessages={() => setDialog("paste")}
          onUploadFiles={() => setDialog("upload")}
        />
      ) : (
        <section className="list-pane">
          {projects.error && (
            <div className="banner" role="alert">
              <p>
                {projects.error.isUnreachable
                  ? `${projects.error.message} Start the backend, or change the address in Server settings.`
                  : projects.error.message}
              </p>
              <button type="button" className="btn" onClick={projects.reload}>
                Try again
              </button>
            </div>
          )}
          {projects.data?.length === 0 && (
            <div className="empty">
              <h2>Create your first project</h2>
              <p>A project holds everything one client has told you, and the requirements pulled out of it.</p>
              <button type="button" className="btn btn-primary" onClick={() => setDialog("project")}>
                New project
              </button>
            </div>
          )}
          {projects.data && projects.data.length > 0 && (
            <div className="empty">
              <h2>Choose a project</h2>
              <p>Pick one from the list to see its requirements.</p>
            </div>
          )}
          {projects.loading && !projects.data && <div className="skeleton" aria-hidden="true" />}
        </section>
      )}

      <div className="detail-pane">
        {project && route.requirementId ? (
          <RequirementPanel
            key={route.requirementId}
            api={api}
            requirementId={route.requirementId}
            onChanged={requirements.reload}
            onBack={() => onOpenProject(project.project_id)}
            notify={notify}
          />
        ) : (
          <div className="empty">
            <h2>Select a requirement</h2>
            <p>
              You'll see what the client actually wrote, which words are unclear, and the full trail from message to
              approval.
            </p>
          </div>
        )}
      </div>

      <IngestDialog
        key={`${route.projectId ?? "none"}-${dialog}`}
        open={(dialog === "paste" || dialog === "upload") && project !== null}
        projectId={project?.project_id ?? ""}
        projectName={project?.name ?? ""}
        mode={dialog === "upload" ? "upload" : "paste"}
        onClose={() => setDialog(null)}
        onSubmitText={addMessages}
        onUploaded={uploaded}
      />
      <NewProjectDialog open={dialog === "project"} onClose={() => setDialog(null)} onCreate={createProject} />
    </div>
  );
}
