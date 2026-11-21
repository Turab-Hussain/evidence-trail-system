# Backend: AI Requirements Evidence Trail System

> Run commands for the whole project are in the root `README.md`. This file describes the backend.

Prototype of the proposal *"AI-Powered Multi-Channel Requirements Management & Evidence Trail
System"*. It turns scattered client communication (email, WhatsApp Business, meeting
transcripts, documents) into structured requirements that are checked for ambiguity,
consolidated across channels, **approved by a human**, confirmed by the client, and tracked in an
auditable evidence trail.

```
Source message -> Extraction -> Ambiguity check -> Consolidation -> PM decision
               -> Client confirmation -> Versioned change history   (= Evidence Trail)
```

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,gemini]"     # "gemini" = Google Gemini extraction (optional)
pytest                             # 91 tests, no network or API key needed
python -m evidence_trail.init_db   # optional: create the database file up front

# Run with Gemini extraction:
export GEMINI_API_KEY=your-key EVIDENCE_LLM_PROVIDER=gemini
python -m evidence_trail           # http://127.0.0.1:8000/docs
python -m evidence_trail.evaluation.run_evaluation  # metrics on data/sample_dataset.json
```

Docker: `docker build -t evidence-trail . && docker run -p 8000:8000 -v evidence-data:/data -e EVIDENCE_DB_PATH=/data/evidence_trail.db evidence-trail`

Configuration is via environment variables (see `.env.example`). With no LLM configured the
extraction agent uses deterministic heuristics, so everything runs offline.

### Gemini
Set `EVIDENCE_LLM_PROVIDER=gemini` and `GEMINI_API_KEY` (or `GOOGLE_API_KEY`). The client
(`llm/gemini_client.py`) uses the `google-genai` SDK in JSON mode at temperature 0. The default model
is the alias `gemini-flash-latest`; set `EVIDENCE_LLM_MODEL` to pin a specific model your key can use.
If a Gemini call fails or returns invalid JSON, extraction falls back to the offline heuristics and
logs a warning, so evidence is never dropped.

## Database
SQLite file (`EVIDENCE_DB_PATH`, default `evidence_trail.db`), created automatically on first start
from `src/evidence_trail/repositories/schema.sql`, or explicitly with `python -m evidence_trail.init_db`.

| Table | Purpose |
|---|---|
| `projects` | Client projects |
| `source_messages` | Raw communication per channel (the evidence; never updated) |
| `requirements` | Living requirements: status, version, priority, confidence |
| `requirement_sources` | Many-to-many provenance: requirement -> source message + exact snippet |
| `ambiguity_findings` | Ambiguity issues + clarification questions |
| `review_events` | PM approve / edit / reject audit records |
| `confirmation_events` | Client confirmation audit records |
| `requirement_versions` | Immutable JSON snapshot per change |
| `evidence_records` | Every pipeline step (ingested, extracted, merged, approved ...) |

Foreign keys are enforced, enum columns have CHECK constraints (a test fails if they drift from
`domain/enums.py`), and multi-statement writes run in a single transaction. PostgreSQL (as in the
proposal) means writing a second `Repository` implementation; no service code changes.

## Architecture (layers, top depends on bottom)

| Layer | Package | Responsibility |
|---|---|---|
| API | `api/` | FastAPI routes, auth, error mapping. No business logic. |
| Services | `services/` | Workflow orchestration: `RequirementPipeline`, `ReviewService`, `ConfirmationService`, `EvidenceTrailService`, `ProjectService`. |
| Agents | `agents/` | Single-responsibility, storage-free steps: extraction, ambiguity, consolidation, confirmation draft, change log. |
| Ingestion | `ingestion/` | One `Ingestor` subclass per channel + `IngestorRegistry`. |
| Domain | `domain/` | Pydantic entities, enums, exceptions. The requirement state machine lives on `Requirement`. |
| Infrastructure | `repositories/`, `llm/` | `Repository` and `LLMClient` abstractions with SQLite / Anthropic implementations. |

`container.py` is the composition root; `config.py` holds settings.

### OOP / best practices applied
- **Encapsulation**: `Requirement.transition_to()` enforces the lifecycle; invalid jumps raise `InvalidStateTransitionError`.
- **Abstraction & polymorphism**: `Agent`, `Ingestor`, `Repository`, `LLMClient` are abstract base classes with swappable implementations.
- **Open/Closed**: a new channel = a new `Ingestor` subclass registered in the registry.
- **Dependency inversion / injection**: services receive abstractions via constructors; wiring happens only in `container.py`.
- **Single responsibility**: agents are pure (domain in, domain out); services persist and orchestrate.
- Type hints everywhere (`mypy --strict` clean), docstrings, `ruff` clean, domain exception hierarchy mapped to HTTP codes, parameterised SQL, salted scrypt password hashes, signed expiring login tokens, per-user data isolation, login rate limiting, evidence saved *before* processing so failures never lose it.

## API summary (every route except `/health`, `/auth/signup` and `/auth/login` needs `Authorization: Bearer <token>`)

| Method & path | Purpose |
|---|---|
| `POST /auth/signup`, `POST /auth/login` | Create an account / sign in; both return `{token, user}` |
| `GET /auth/me`, `GET /me/dashboard` | Signed-in user; profile plus totals, per-project summaries and recent activity |
| `POST /projects`, `GET /projects` | Create / list **your** projects (other users' projects are invisible: 404) |
| `POST /projects/{id}/upload` | Multipart upload of `.pdf .docx .txt .md .eml .vtt .srt .csv` (max 10 files, 5 MB each, optional `channel`) |
| `POST /projects/{id}/ingest/{email\|transcript\|document}` | Ingest text `{content, sender?, timestamp?}` |
| `POST /projects/{id}/webhooks/whatsapp` | Official WhatsApp Cloud API webhook payload |
| `GET /projects/{id}/requirements?status=&q=` | Search / filter |
| `GET /projects/{id}/dashboard` | Counts by status and ambiguity type |
| `GET /requirements/{id}` | Requirement + ambiguity findings |
| `POST /requirements/{id}/review` | PM approve / edit / reject |
| `GET /requirements/{id}/confirmation-draft` | Client message (approved requirements only) |
| `POST /requirements/{id}/confirmation` | Record client confirmed / changes requested |
| `GET /requirements/{id}/trail` | Chronological evidence trail + completeness flag |

## Honest scope notes
- The proposal was a research document, so this is a **new prototype built from it**, not a refactor of existing code.
- Heuristic extraction and rule-based ambiguity/consolidation are simple baselines. The Gemini and Anthropic paths are implemented but **tests use fake SDK clients; they were never run against the live APIs**. Gemini model names change often, so pin one with `EVIDENCE_LLM_MODEL` if the default alias is unavailable to your key.
- SQLite suits a prototype/single server. There is no migration tool: the schema uses `IF NOT EXISTS`, plus one built-in step that adds `projects.owner_id` to databases made before accounts existed (the first account created then adopts those projects).
- Accounts are email + password only: no email verification, password reset or roles. The login rate limit is in memory (per process). Scanned PDFs (no text layer) and old `.doc` files are rejected with a clear message.
- Consolidation uses token similarity, not a vector DB (ChromaDB). WhatsApp support parses webhook payloads only (no sending, no signature verification yet).
- Not yet built: XLSX parsing, OCR for scanned PDFs, IMAP polling, roles and teams, baseline comparison (Phase 9).
- `data/sample_dataset.json` is a tiny synthetic demo; its 1.0 scores say nothing about real accuracy.
