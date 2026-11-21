import type {
  AuthResponse,
  Channel,
  ClientResponse,
  EvidenceTrail,
  IngestResult,
  MeResponse,
  Project,
  Requirement,
  RequirementDetail,
  RequirementListItem,
  ReviewInput,
  UploadResponse,
} from "../types";
import { normaliseApiUrl, type ApiSettings } from "../lib/settings";

/** Any failure talking to the API. ``status`` is ``null`` when the server was unreachable. */
export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number | null,
  ) {
    super(message);
    this.name = "ApiError";
  }

  get isUnreachable(): boolean {
    return this.status === null;
  }

  get isUnauthorised(): boolean {
    return this.status === 401;
  }

  /** True when the server says the request was well-formed but the values were not acceptable. */
  get isInvalid(): boolean {
    return this.status === 422;
  }
}

/** Text channels map to ``/ingest/<name>``; WhatsApp has its own webhook route. */
const TEXT_CHANNEL_PATH: Record<Exclude<Channel, "whatsapp">, string> = {
  email: "email",
  meeting_transcript: "transcript",
  document: "document",
};

/**
 * Wrap plain text in the WhatsApp Cloud API webhook shape the backend parses,
 * so people can paste a message instead of hand-writing JSON.
 */
export function toWhatsAppPayload(text: string, sender: string): object {
  return {
    entry: [
      {
        changes: [
          {
            value: {
              messages: [
                {
                  from: sender || "client",
                  type: "text",
                  timestamp: String(Math.floor(Date.now() / 1000)),
                  text: { body: text },
                },
              ],
            },
          },
        ],
      },
    ],
  };
}

/** Pull a readable message out of FastAPI's ``{"detail": ...}`` error bodies. */
function describeDetail(detail: unknown, fallback: string): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => (item && typeof item === "object" && "msg" in item ? String(item.msg) : null))
      .filter((m): m is string => m !== null);
    if (messages.length > 0) return messages.join("; ");
  }
  return fallback;
}

/** Channel names accepted by the upload endpoint (``null`` lets the server decide from the file type). */
export type UploadChannel = "email" | "transcript" | "document";

/** Thin, typed wrapper around the backend REST API. */
export class ApiClient {
  private readonly baseUrl: string;

  /**
   * @param settings    Where the backend is.
   * @param token       The signed-in user's token, or ``null`` before sign-in.
   * @param onSessionEnded Called when the server rejects the token (expired or invalid).
   */
  constructor(
    settings: ApiSettings,
    private readonly token: string | null = null,
    private readonly onSessionEnded: () => void = () => undefined,
  ) {
    this.baseUrl = normaliseApiUrl(settings.apiUrl);
  }

  private async request<T>(
    path: string,
    init: { method?: "GET" | "POST"; body?: unknown; form?: FormData } = {},
  ): Promise<T> {
    const headers: Record<string, string> = { Accept: "application/json" };
    if (init.body !== undefined) headers["Content-Type"] = "application/json";
    if (this.token) headers.Authorization = `Bearer ${this.token}`;

    let response: Response;
    try {
      response = await fetch(`${this.baseUrl}${path}`, {
        method: init.method ?? "GET",
        headers, // for FormData the browser adds the multipart boundary itself
        body: init.form ?? (init.body === undefined ? undefined : JSON.stringify(init.body)),
      });
    } catch {
      throw new ApiError(`Can't reach the API at ${this.baseUrl}.`, null);
    }

    if (!response.ok) {
      let detail: unknown;
      try {
        detail = (await response.json()).detail;
      } catch {
        /* non-JSON error body */
      }
      // A 401 with a token means the session ended; without one it is just a wrong password.
      if (response.status === 401 && this.token) this.onSessionEnded();
      throw new ApiError(describeDetail(detail, `Request failed (${response.status}).`), response.status);
    }
    return (await response.json()) as T;
  }

  // -- accounts ---------------------------------------------------------------
  signup(name: string, email: string, password: string): Promise<AuthResponse> {
    return this.request("/auth/signup", { method: "POST", body: { name, email, password } });
  }

  login(email: string, password: string): Promise<AuthResponse> {
    return this.request("/auth/login", { method: "POST", body: { email, password } });
  }

  /** The signed-in user plus the dashboard figures across all of their projects. */
  getMe(): Promise<MeResponse> {
    return this.request("/me/dashboard");
  }

  // -- projects and requirements ----------------------------------------------
  listProjects(): Promise<Project[]> {
    return this.request("/projects");
  }

  createProject(name: string, client: string): Promise<Project> {
    return this.request("/projects", { method: "POST", body: { name, client } });
  }

  listRequirements(projectId: string): Promise<RequirementListItem[]> {
    return this.request(`/projects/${encodeURIComponent(projectId)}/requirements`);
  }

  getRequirement(requirementId: string): Promise<RequirementDetail> {
    return this.request(`/requirements/${encodeURIComponent(requirementId)}`);
  }

  getTrail(requirementId: string): Promise<EvidenceTrail> {
    return this.request(`/requirements/${encodeURIComponent(requirementId)}/trail`);
  }

  review(requirementId: string, input: ReviewInput): Promise<Requirement> {
    return this.request(`/requirements/${encodeURIComponent(requirementId)}/review`, {
      method: "POST",
      body: input,
    });
  }

  async getConfirmationDraft(requirementId: string): Promise<string> {
    const result = await this.request<{ draft: string }>(
      `/requirements/${encodeURIComponent(requirementId)}/confirmation-draft`,
    );
    return result.draft;
  }

  recordConfirmation(requirementId: string, response: ClientResponse, note?: string): Promise<Requirement> {
    return this.request(`/requirements/${encodeURIComponent(requirementId)}/confirmation`, {
      method: "POST",
      body: { response, note: note || null },
    });
  }

  ingest(projectId: string, channel: Channel, content: string, sender: string): Promise<IngestResult> {
    const id = encodeURIComponent(projectId);
    if (channel === "whatsapp") {
      return this.request(`/projects/${id}/webhooks/whatsapp`, {
        method: "POST",
        body: toWhatsAppPayload(content, sender),
      });
    }
    return this.request(`/projects/${id}/ingest/${TEXT_CHANNEL_PATH[channel]}`, {
      method: "POST",
      body: { content, sender: sender || null },
    });
  }

  /** Upload PDF / Word / text / email / caption files; each is read and processed on the server. */
  uploadFiles(projectId: string, files: File[], channel: UploadChannel | null): Promise<UploadResponse> {
    const form = new FormData();
    for (const file of files) form.append("files", file, file.name);
    if (channel) form.append("channel", channel);
    return this.request(`/projects/${encodeURIComponent(projectId)}/upload`, { method: "POST", form });
  }
}
