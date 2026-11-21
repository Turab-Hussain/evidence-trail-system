/** Types mirroring the backend API (see backend/src/evidence_trail/domain and api/schemas.py). */

export type Channel = "email" | "whatsapp" | "meeting_transcript" | "document";

export type RequirementStatus =
  | "pending_approval"
  | "approved"
  | "rejected"
  | "confirmed"
  | "changes_requested";

export type RequirementType = "functional" | "non_functional";
export type Priority = "high" | "medium" | "low";
export type AmbiguityType = "vague_term" | "missing_constraint" | "conflict";
export type ReviewDecision = "approve" | "edit" | "reject";
export type ClientResponse = "confirmed" | "changes_requested";

export interface Project {
  project_id: string;
  name: string;
  client: string;
  status: string;
  owner_id: string | null;
}

export interface SourceReference {
  source_id: string;
  snippet: string;
}

export interface Requirement {
  requirement_id: string;
  project_id: string;
  title: string;
  description: string;
  type: RequirementType;
  priority: Priority;
  confidence: number;
  status: RequirementStatus;
  version: number;
  sources: SourceReference[];
  created_at: string;
  updated_at: string;
}

/** A requirement in the list view, with its number of open ambiguity findings. */
export interface RequirementListItem extends Requirement {
  open_findings: number;
}

export interface SourceMessage {
  source_id: string;
  project_id: string;
  channel: Channel;
  timestamp: string;
  sender: string | null;
  sender_role: string | null;
  content: string;
  evidence_uri: string;
}

export interface AmbiguityFinding {
  finding_id: string;
  requirement_id: string;
  issue_type: AmbiguityType;
  explanation: string;
  clarification_question: string;
}

export interface RequirementDetail {
  requirement: Requirement;
  findings: AmbiguityFinding[];
  sources: SourceMessage[];
}

export type TrailKind =
  | "source"
  | "ai_step"
  | "ambiguity"
  | "pm_decision"
  | "client_confirmation"
  | "version"
  | "other";

export interface TrailEntry {
  timestamp: string;
  kind: TrailKind;
  actor: string;
  summary: string;
  reference: string | null;
}

export interface EvidenceTrail {
  requirement_id: string;
  entries: TrailEntry[];
  complete: boolean;
  missing: string[];
}

export interface IngestResult {
  source_ids: string[];
  created_requirements: string[];
  updated_requirements: string[];
  failed_sources: string[];
}

export interface ReviewInput {
  decision: ReviewDecision;
  edited_title?: string;
  edited_description?: string;
  note?: string;
}

/** The signed-in account, as returned by the API (never includes the password). */
export interface User {
  user_id: string;
  name: string;
  email: string;
  created_at: string;
  last_login_at: string | null;
}

export interface AuthResponse {
  token: string;
  user: User;
}

export interface ProjectSummary {
  project: Project;
  requirements: number;
  sources: number;
  by_status: Partial<Record<RequirementStatus, number>>;
  open_findings: number;
  last_activity: string | null;
}

export interface ActivityItem {
  timestamp: string;
  step: string;
  detail: string;
  actor: string;
  project_id: string;
  project_name: string;
  requirement_id: string | null;
  requirement_title: string | null;
}

export interface AccountDashboard {
  projects: number;
  sources: number;
  requirements: number;
  awaiting_review: number;
  confirmed: number;
  open_findings: number;
  by_status: Record<RequirementStatus, number>;
  by_channel: Record<Channel, number>;
  project_summaries: ProjectSummary[];
  recent_activity: ActivityItem[];
}

export interface MeResponse {
  user: User;
  dashboard: AccountDashboard;
}

export interface UploadResult {
  filename: string;
  ok: boolean;
  channel: Channel | null;
  characters: number;
  error: string | null;
  created_requirements: string[];
  updated_requirements: string[];
  failed_sources: string[];
}

export interface UploadResponse {
  results: UploadResult[];
  supported_types: string[];
}
