import { useCallback, useEffect, useState } from "react";

export type Page = "login" | "signup" | "dashboard" | "projects" | "project";

export interface Route {
  page: Page;
  projectId: string | null;
  requirementId: string | null;
}

/**
 * Parse the URL hash:
 *   #/login  #/signup  #/dashboard  #/projects  #/p/<project>[/r/<requirement>]
 * Anything else is the dashboard (the guard in App sends signed-out users to login).
 */
export function parseHash(hash: string): Route {
  const project = /^#\/p\/([^/]+)(?:\/r\/([^/]+))?/.exec(hash);
  if (project) {
    return {
      page: "project",
      projectId: decodeURIComponent(project[1]),
      requirementId: project[2] ? decodeURIComponent(project[2]) : null,
    };
  }
  if (hash.startsWith("#/login")) return { page: "login", projectId: null, requirementId: null };
  if (hash.startsWith("#/signup")) return { page: "signup", projectId: null, requirementId: null };
  if (hash.startsWith("#/projects")) return { page: "projects", projectId: null, requirementId: null };
  return { page: "dashboard", projectId: null, requirementId: null };
}

export function buildHash(projectId: string | null, requirementId: string | null): string {
  if (!projectId) return "#/dashboard";
  const base = `#/p/${encodeURIComponent(projectId)}`;
  return requirementId ? `${base}/r/${encodeURIComponent(requirementId)}` : base;
}

export interface Navigation {
  route: Route;
  /** Open a project, optionally with one requirement selected. */
  openProject: (projectId: string, requirementId?: string | null) => void;
  /** Open one of the top-level pages. */
  openPage: (page: Exclude<Page, "project">) => void;
}

/** Keep the current page in the URL so links, refresh and the back button work. */
export function useHashRoute(): Navigation {
  const [route, setRoute] = useState<Route>(() => parseHash(window.location.hash));

  useEffect(() => {
    const onChange = () => setRoute(parseHash(window.location.hash));
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);

  const openProject = useCallback((projectId: string, requirementId: string | null = null) => {
    window.location.hash = buildHash(projectId, requirementId);
  }, []);

  const openPage = useCallback((page: Exclude<Page, "project">) => {
    window.location.hash = `#/${page}`;
  }, []);

  return { route, openProject, openPage };
}
