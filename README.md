# AI Requirements Evidence Trail System

Turns scattered client communication (WhatsApp, email, meeting transcripts, documents) into
verified, traceable requirements: extracted by AI (Gemini or built-in rules), checked for unclear
wording, merged across channels, **approved by a project manager**, confirmed by the client, and
kept in an auditable evidence trail.

```
evidence-trail-system/
├── backend/    Python 3.11+  FastAPI + SQLite   (REST API, agents, tests)   → backend/README.md
├── frontend/   React + TypeScript + Vite       (the review desk UI)
└── docker-compose.yml
```

## Run it (two terminals)

**Prerequisites:** Python 3.11+, Node.js 20+.

### 1. Backend (terminal 1)

Windows (PowerShell):
```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev,gemini]"
# optional, for Gemini instead of the built-in rules:
# $env:GEMINI_API_KEY = "your-key"; $env:EVIDENCE_LLM_PROVIDER = "gemini"
python -m evidence_trail
```

macOS / Linux:
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,gemini]"
# optional: export GEMINI_API_KEY=your-key EVIDENCE_LLM_PROVIDER=gemini
python -m evidence_trail
```
API on http://127.0.0.1:8000 (interactive docs at `/docs`). The database file `evidence_trail.db` is created automatically.

### 2. Frontend (terminal 2)
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:5173 and **create an account** (name, email, password of 8+ characters;
there is no separate API key). Then **New project** → **Add client messages** (the *Fill with an
example* button gives you sample text) or **Upload files**.

### Or with Docker
```bash
docker compose up --build        # UI: http://localhost:8080   API: http://localhost:8000/docs
```
(Not tested in the environment this was built in; see Honest notes.)

## Using the app
0. **Sign up / sign in.** Each account sees only its own projects. The **Dashboard** shows your account details, totals (projects, messages, requirements, what needs review), a status breakdown, a table of your projects with quick actions, and recent activity.
1. **Add client messages** from WhatsApp, email, a meeting transcript or a document: paste text, or **upload files** (PDF, Word `.docx`, `.txt`, `.md`, `.eml`, `.vtt`/`.srt` captions; drag and drop, up to 10 files of 5 MB). Each file is reported separately, so one bad file doesn't block the rest, and the file name is kept as the source in the evidence trail.
2. Each message becomes one or more requirements. The same request arriving on two channels merges into one requirement (version 2) with both quotes kept.
3. Open a requirement: the client's own words appear in serif, with **unclear words highlighted** and ready-made questions to ask the client.
4. **Approve**, **Edit, then approve**, or **Reject**. Nothing is final until a person decides.
5. **Write message for the client**, copy it, then record **Client confirmed** or **Client asked for changes**.
6. The **evidence trail** shows the whole journey, each step timestamped and attributed.

## Tests and checks
```bash
cd backend  && pytest && ruff check src tests && mypy src     # 91 tests
cd frontend && npm test && npm run typecheck && npm run build  # 27 tests
```

## Honest notes
- The UI and API were exercised end to end in headless Chrome (sign up, wrong password, dashboard, upload of Word + PDF + text files with a bad file rejected, workspace, refresh keeps the session, sign out and back in, a second account seeing none of the first one's data, mobile layout). Gemini was **not** called against the live API (no key here); tests use a fake client. Docker files were **not** run here.
- Extraction without an LLM is rule-based and simple: it finds sentences with request words ("need", "must", "add"...). Gemini should do noticeably better on messy messages.
- The login token is kept in the browser's local storage: fine for a prototype; a production app would use secure, HTTP-only cookies and HTTPS. There is no email verification or password reset, and no roles or teams yet.
- Scanned (image-only) PDFs can't be read, and old `.doc` files aren't supported; export them as text-based PDF or `.docx`.
- Not built: PostgreSQL, IMAP polling, OCR, baseline comparison for the evaluation plan.
