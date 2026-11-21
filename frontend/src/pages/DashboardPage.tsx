import { useState } from "react";
import { ActivityFeed } from "../components/dashboard/ActivityFeed";
import { ChannelBreakdown, StatusBreakdown } from "../components/dashboard/Breakdowns";
import { ProfileCard } from "../components/dashboard/ProfileCard";
import { ProjectsTable } from "../components/dashboard/ProjectsTable";
import { StatTiles } from "../components/dashboard/StatTiles";
import { IngestDialog } from "../components/dialogs/IngestDialog";
import { NewProjectDialog } from "../components/dialogs/NewProjectDialog";
import { useAuth } from "../context/AuthContext";
import { useNotify } from "../context/ToastContext";
import { plural } from "../lib/format";
import { useResource } from "../lib/useResource";
import type { Channel, ProjectSummary, UploadResponse } from "../types";

interface DashboardPageProps {
  onOpenProject: (projectId: string, requirementId?: string | null) => void;
}

/** The signed-in user's overview: account details, totals, projects and recent activity. */
export function DashboardPage({ onOpenProject }: DashboardPageProps) {
  const { api, user: signedIn, logout } = useAuth();
  const notify = useNotify();
  const me = useResource(() => api.getMe(), [api]);
  const [creating, setCreating] = useState(false);
  const [uploadFor, setUploadFor] = useState<ProjectSummary | null>(null);

  const user = me.data?.user ?? signedIn;
  const data = me.data?.dashboard ?? null;

  async function createProject(name: string, client: string) {
    const created = await api.createProject(name, client);
    setCreating(false);
    notify(`Created ${created.name}`);
    onOpenProject(created.project_id);
  }

  async function addText(channel: Channel, content: string, sender: string) {
    if (!uploadFor) return;
    const result = await api.ingest(uploadFor.project.project_id, channel, content, sender);
    setUploadFor(null);
    me.reload();
    notify(`Added ${plural(result.source_ids.length, "message")}.`);
  }

  function uploaded(response: UploadResponse) {
    me.reload();
    const ok = response.results.filter((result) => result.ok).length;
    if (ok > 0) notify(`Read ${plural(ok, "file")}.`);
  }

  return (
    <main className="page dashboard">
      <header className="page-head">
        <div>
          <h1>Dashboard</h1>
          <p>{user ? `Welcome back, ${user.name.split(" ")[0]}.` : ""}</p>
        </div>
        <button type="button" className="btn btn-primary" onClick={() => setCreating(true)}>
          New project
        </button>
      </header>

      {me.error && !data && (
        <div className="banner" role="alert">
          <p>
            {me.error.isUnreachable
              ? `${me.error.message} Start the backend, then try again.`
              : me.error.message}
          </p>
          <button type="button" className="btn" onClick={me.reload}>
            Try again
          </button>
        </div>
      )}

      <div className="dash-grid">
        {user && <ProfileCard user={user} onSignOut={logout} />}
        <div className="dash-main">
          {data ? (
            <>
              <StatTiles data={data} />
              <div className="split">
                <StatusBreakdown data={data} />
                <ChannelBreakdown data={data} />
              </div>
              <ProjectsTable
                summaries={data.project_summaries}
                onOpen={(projectId) => onOpenProject(projectId)}
                onUpload={setUploadFor}
                onNewProject={() => setCreating(true)}
              />
              <ActivityFeed items={data.recent_activity} onOpen={onOpenProject} />
            </>
          ) : (
            !me.error && <div className="skeleton" aria-hidden="true" />
          )}
        </div>
      </div>

      <NewProjectDialog open={creating} onClose={() => setCreating(false)} onCreate={createProject} />
      <IngestDialog
        key={uploadFor?.project.project_id ?? "none"}
        open={uploadFor !== null}
        projectId={uploadFor?.project.project_id ?? ""}
        projectName={uploadFor?.project.name ?? ""}
        mode="upload"
        onClose={() => setUploadFor(null)}
        onSubmitText={addText}
        onUploaded={uploaded}
      />
    </main>
  );
}
