-- Relational schema for the AI Requirements Evidence Trail System (SQLite).
-- Loaded automatically by SQLiteRepository; safe to run repeatedly (IF NOT EXISTS).
-- Timestamps are stored as ISO-8601 UTC text. Foreign keys are enforced
-- (PRAGMA foreign_keys = ON is set per connection by the repository).
--
-- NOTE: the CHECK lists mirror domain/enums.py; tests/test_database.py fails if they drift.

CREATE TABLE IF NOT EXISTS users (
    user_id       TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    last_login_at TEXT
);

-- Server-side secrets (e.g. the key that signs login tokens), generated on first start.
CREATE TABLE IF NOT EXISTS app_secrets (
    name  TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS projects (
    project_id   TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    client       TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'active',
    owner_id     TEXT REFERENCES users(user_id)
);

-- Raw client communication. Never updated or deleted: this is the evidence.
CREATE TABLE IF NOT EXISTS source_messages (
    source_id    TEXT PRIMARY KEY,
    project_id   TEXT NOT NULL REFERENCES projects(project_id),
    channel      TEXT NOT NULL
                 CHECK (channel IN ('email', 'whatsapp', 'meeting_transcript', 'document')),
    timestamp    TEXT NOT NULL,
    sender       TEXT,
    sender_role  TEXT,
    content      TEXT NOT NULL,
    evidence_uri TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS requirements (
    requirement_id TEXT PRIMARY KEY,
    project_id     TEXT NOT NULL REFERENCES projects(project_id),
    title          TEXT NOT NULL,
    description    TEXT NOT NULL,
    type           TEXT NOT NULL CHECK (type IN ('functional', 'non_functional')),
    priority       TEXT NOT NULL CHECK (priority IN ('high', 'medium', 'low')),
    confidence     REAL NOT NULL CHECK (confidence BETWEEN 0.0 AND 1.0),
    status         TEXT NOT NULL CHECK (status IN
                   ('pending_approval', 'approved', 'rejected', 'confirmed', 'changes_requested')),
    version        INTEGER NOT NULL CHECK (version >= 1),
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL
);

-- Many-to-many provenance: which messages (and which exact text) support a requirement.
CREATE TABLE IF NOT EXISTS requirement_sources (
    requirement_id TEXT NOT NULL REFERENCES requirements(requirement_id) ON DELETE CASCADE,
    position       INTEGER NOT NULL,
    source_id      TEXT NOT NULL REFERENCES source_messages(source_id),
    snippet        TEXT NOT NULL,
    PRIMARY KEY (requirement_id, position)
);

CREATE TABLE IF NOT EXISTS ambiguity_findings (
    finding_id             TEXT PRIMARY KEY,
    requirement_id         TEXT NOT NULL REFERENCES requirements(requirement_id) ON DELETE CASCADE,
    issue_type             TEXT NOT NULL
                           CHECK (issue_type IN ('vague_term', 'missing_constraint', 'conflict')),
    explanation            TEXT NOT NULL,
    clarification_question TEXT NOT NULL
);

-- Audit tables below are append-only by convention (the application never updates them).
CREATE TABLE IF NOT EXISTS review_events (
    event_id       TEXT PRIMARY KEY,
    requirement_id TEXT NOT NULL REFERENCES requirements(requirement_id),
    actor          TEXT NOT NULL,
    decision       TEXT NOT NULL CHECK (decision IN ('approve', 'edit', 'reject')),
    edited_content TEXT,
    note           TEXT,
    timestamp      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS confirmation_events (
    confirmation_id TEXT PRIMARY KEY,
    requirement_id  TEXT NOT NULL REFERENCES requirements(requirement_id),
    client_response TEXT NOT NULL CHECK (client_response IN ('confirmed', 'changes_requested')),
    note            TEXT,
    actor           TEXT NOT NULL,
    timestamp       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS requirement_versions (
    version_id     TEXT PRIMARY KEY,
    requirement_id TEXT NOT NULL REFERENCES requirements(requirement_id),
    version_number INTEGER NOT NULL CHECK (version_number >= 1),
    changes        TEXT NOT NULL,
    author         TEXT NOT NULL,
    snapshot       TEXT NOT NULL,          -- JSON copy of the requirement at that moment
    timestamp      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence_records (
    evidence_id         TEXT PRIMARY KEY,
    source_id           TEXT REFERENCES source_messages(source_id),
    requirement_id      TEXT REFERENCES requirements(requirement_id),
    transformation_step TEXT NOT NULL,
    output_ref          TEXT NOT NULL,
    detail              TEXT NOT NULL DEFAULT '',
    actor               TEXT NOT NULL DEFAULT 'system',
    timestamp           TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_projects_owner      ON projects(owner_id);
CREATE INDEX IF NOT EXISTS idx_sources_project      ON source_messages(project_id);
CREATE INDEX IF NOT EXISTS idx_requirements_project ON requirements(project_id, status);
CREATE INDEX IF NOT EXISTS idx_reqsources_source    ON requirement_sources(source_id);
CREATE INDEX IF NOT EXISTS idx_findings_req         ON ambiguity_findings(requirement_id);
CREATE INDEX IF NOT EXISTS idx_reviews_req          ON review_events(requirement_id);
CREATE INDEX IF NOT EXISTS idx_confirmations_req    ON confirmation_events(requirement_id);
CREATE INDEX IF NOT EXISTS idx_versions_req         ON requirement_versions(requirement_id);
CREATE INDEX IF NOT EXISTS idx_evidence_req         ON evidence_records(requirement_id);
CREATE INDEX IF NOT EXISTS idx_evidence_source      ON evidence_records(source_id);
