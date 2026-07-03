# GSEB PARAKH / NAS Competency Assessment Platform
### Full-Stack AI-Powered MVP — Build Specification

> **Goal:** A fully Dockerized, local-first, AI-powered assessment platform that lets teachers turn a chapter PDF into competency-tagged MCQs, model papers, OMR sheets, and analytics — demo-ready for a District Education Officer (DEO) in under 2 days, with zero recurring cost.

---

## 1. Executive Summary

| | |
|---|---|
| **What it is** | A platform that mirrors GSEB PARAKH / NAS-style competency-based assessment, end-to-end: PDF → AI analysis → questions → papers → OMR → results → analytics → reports. |
| **Who it's for** | Teachers, Principals, DEOs, and a platform Admin. |
| **Why local AI** | Zero recurring cost, works offline, no data leaves the machine — important for student data and government demos. |
| **Definition of done** | `docker compose up --build` brings up the full stack and the demo flow in Section 12 works start to finish with seeded data. |

---

## 2. Tech Stack

| Layer | Choice | Notes |
|---|---|---|
| Backend | Python 3.12, FastAPI, Pydantic v2, Uvicorn | Async-first |
| ORM / Migrations | SQLAlchemy 2.0, Alembic | See §4 for DB strategy |
| Database | SQLite (MVP) → PostgreSQL (production path) | Schema must be Postgres-compatible from day one (see §4.1) |
| AI Runtime | Ollama, local only | No OpenAI / Claude / Gemini / cloud APIs of any kind |
| Default model | `qwen3:8b` | |
| Fallback models | `gemma3:12b`, `llama3.1:8b` | Auto-fallback on timeout/failure (see §8.4) |
| PDF parsing | PyMuPDF (primary), pdfplumber (table/layout fallback) | |
| OMR processing | OpenCV, NumPy, Pillow | |
| Report/PDF generation | ReportLab, Matplotlib, Pandas | |
| Frontend | React + Vite + TypeScript, Tailwind, shadcn/ui, Framer Motion, Recharts, Lucide | |
| Auth | JWT, demo credentials, RBAC | |
| Containerization | Docker, Docker Compose | |

**Hard constraints:**
- No cloud AI providers, no paid APIs, no API keys required to run.
- Entire stack must run offline after first `docker compose up --build` (which pulls the Ollama model once).

---

## 3. System Architecture

```
┌──────────────┐      ┌──────────────────┐      ┌───────────────────┐
│ React + Vite │ HTTP │  FastAPI Backend  │ SQL  │  SQLite/Postgres  │
│  (Frontend)  │ ───▶ │   (API + Auth)    │ ───▶ │     (Database)    │
└──────────────┘      └─────────┬─────────┘      └───────────────────┘
                                 │ HTTP (internal)
                                 ▼
                       ┌───────────────────┐
                       │   Ollama Engine   │
                       │  (qwen3:8b, etc.) │
                       └───────────────────┘
```

**Containers:** `frontend`, `backend`, `ollama` (DB is a file/volume in MVP, becomes its own container on the Postgres path — see §4.1).

**Key principle:** the backend never calls the LLM synchronously inside a request that blocks the UI thread for more than a few seconds — long AI jobs (chapter analysis, question generation) are async background jobs with polling/status endpoints (see §8).

---

## 4. Data Layer

### 4.1 SQLite-to-Postgres Compatibility Rules
To make "SQLite now, Postgres later" actually true rather than aspirational:
- Use SQLAlchemy types that map cleanly to both (`String`, `Integer`, `Float`, `Boolean`, `DateTime`, `JSON` — avoid SQLite-only pragmas).
- Use `UUID` (stored as `String(36)`) for all primary keys, not autoincrement integers — avoids ID collisions if data is ever merged across environments.
- All migrations go through Alembic from commit #1, even in SQLite. Never hand-edit the schema.
- No raw SQL with SQLite-specific syntax (e.g. `INSERT OR IGNORE`) — use SQLAlchemy-level upserts.

### 4.2 Core Entities (SQLAlchemy Models)

| Model | Key Fields | Relationships |
|---|---|---|
| `User` | id, name, email, password_hash, role (admin/teacher/principal/deo) | → School |
| `School` | id, name, district, udise_code | → Students, Users |
| `Student` | id, name, roll_number, grade, school_id | → School, Results |
| `Chapter` | id, title, grade, subject, description, file_path, status | → Concepts, extraction record |
| `Concept` | id, chapter_id, name, bloom_level | → Competencies |
| `Competency` | id, name, code, description | → Questions (M2M) |
| `Question` | id, text, options(JSON), correct_answer, difficulty, explanation, status (draft/approved/rejected) | → Competency, Chapter |
| `QuestionPaper` | id, grade, subject, title, question_ids(JSON) | → PaperVariants |
| `PaperVariant` | id, paper_id, variant_label (A/B/C…), shuffled_question_order(JSON), pdf_path | → QuestionPaper |
| `Assessment` | id, name, paper_id, school_id, date | → OMRSheets, Results |
| `OMRSheet` | id, assessment_id, student_id, pdf_path, scanned_image_path | → Assessment, Result |
| `Result` | id, omr_sheet_id, score, correct_count, incorrect_count, competency_breakdown(JSON) | → OMRSheet |
| `Report` | id, type (student/class/school/assessment), target_id, pdf_path, generated_at | — |
| `AnalysisCache` | id, chapter_file_hash, analysis_json, questions_json, created_at | Keyed by content hash, see §9 |

> Every model gets `created_at` / `updated_at`. Use Alembic autogenerate + manual review for each migration.

---

## 5. Authentication & Roles

- JWT-based auth with refresh tokens; demo seed accounts for all 4 roles (e.g. `teacher@demo.local` / `Demo@123`).
- Role-based dashboard routing: `Admin`, `Teacher`, `Principal`, `DEO` each land on a distinct dashboard after login.
- "Remember me" persists refresh token in httpOnly cookie (not localStorage).
- Protected routes on frontend (route guard by role) **and** enforced server-side (role check on every endpoint) — frontend guards are UX only, never the security boundary.

---

## 6. UI/UX Direction

**Visual language:** dark theme, glassmorphism panels, restrained motion (Framer Motion for state transitions, not decoration), inspired by Linear/Notion/Vercel/Stripe/Clerk — i.e. confident whitespace, one accent color, no rainbow dashboards.

**Required surfaces:**
- Login + role selection
- Dashboard (role-specific KPIs + charts)
- Chapter Library (upload, list, status)
- AI Analysis viewer (concepts/competencies/Bloom levels as structured, editable cards — not a JSON dump)
- Question Bank (filterable table: grade, subject, competency, difficulty, status)
- Paper Builder (variant count, live preview)
- OMR Sheet preview/download
- OMR Upload & Evaluation results view
- Analytics (district/school/assessment/student tabs)
- Reports library

**Non-goal:** this should not look like a generic CRUD admin panel — invest design effort in the Dashboard, Question Bank, and Analytics screens specifically, since those are what a DEO will actually look at.

---

## 7. Functional Modules

### Module 1 — Chapter Library
- Upload PDF with metadata: Grade, Subject, Chapter Name, Description.
- Store file on disk (`/uploads`), record path + metadata in DB.
- List view: file name, upload date, processing status (`uploaded → extracted → analyzed → questions_ready`), grade, subject.

### Module 2 — PDF Extraction Engine
- PyMuPDF for text extraction; pdfplumber as fallback for complex layouts/tables.
- Persist: page count, word count, full extracted text, and a short preview (first ~500 chars) for the UI.
- Extraction is idempotent — re-uploading an identical file (same hash) reuses the cached extraction.

### Module 3 — AI Chapter Analysis
- Send extracted text to Ollama with a structured-output prompt requesting: chapter name, concepts, learning outcomes, competencies, Bloom levels, common misconceptions.
- **Strict JSON contract** — see §8.2 for the schema and validation/retry strategy.
- Persist validated result; surface in UI as editable structured cards (teacher can correct AI output before it feeds question generation).

### Module 4 — AI Question Generation
- Generate MCQs from approved concepts/competencies. Categories: concept-based, application-based, reasoning-based, competency-based — explicitly avoid rote memorization questions (this is a prompt-engineering requirement, not just a label).
- Difficulty distribution: 40% Easy / 40% Medium / 20% Hard (enforced post-generation by counting and re-requesting if the distribution drifts beyond ±5%).
- Each question stores: text, 4 options, correct answer, difficulty, competency tag, and a generated explanation for the correct answer.

### Module 5 — Question Bank
- Full CRUD + workflow states: Draft → Approved → Rejected.
- Search, filter (subject/grade/competency/difficulty/status), bulk approve/reject.
- Edits to AI-generated questions are tracked (so "human-edited" vs "AI-original" is visible — useful for a DEO demo and for quality control).

### Module 6 — Model Paper Generation
- Teacher selects grade, subject, question count, number of variants (up to 30).
- Each variant independently shuffles question order **and** option order per question (tracking the shuffle map so the answer key stays correct per variant).
- Render to PDF (ReportLab) with consistent letterhead/branding.

### Module 7 — Answer Key Generation
- Auto-derived from each variant's shuffle map (not regenerated from scratch — must be 100% consistent with the variant PDF).
- Export PDF with: question number, correct answer, competency, difficulty.

### Module 8 — OMR Sheet Generation
- Professional OMR layout: student name, roll number, school, assessment ID, QR code (encodes assessment_id + student_id for fast lookup on scan), barcode, bubble grid.
- Support 20 / 40 / 60-question layouts.
- Output as print-ready PDF.

### Module 9 — OMR Evaluation Engine
Real OpenCV pipeline, not a mock:
1. Upload scanned/photographed OMR image.
2. Detect corner/alignment markers.
3. Perspective-correct (homography transform) to a canonical layout.
4. Detect filled bubbles (thresholding + contour analysis per bubble region).
5. Decode QR/barcode to identify student + assessment, then look up the correct answer key for that student's specific paper variant.
6. Compare, score, and persist a `Result` with competency-level breakdown.
7. Return a confidence flag for ambiguous bubbles (e.g. partially filled, multiple marks) for manual review rather than silently guessing.

### Module 10 — Analytics Engine
- Aggregation levels: District, School, Assessment, Student.
- Chart types: bar, line, pie, radar (competency spread), heatmap (grade × competency strength/weakness).
- Surfaces weak vs. strong competencies, subject trends, grade trends.

### Module 11 — Report Generation
- PDF reports (ReportLab + Matplotlib charts embedded) for: Student, Class, School, Assessment levels.
- Each includes: performance summary, competency analysis, charts, and templated recommendations (e.g. "Below-average performance in [competency] — consider remedial focus on [concept]").

---

## 8. AI Service Layer (the part that actually has to work reliably)

### 8.1 Service Interface
```
analyze_chapter(text) -> ChapterAnalysis
generate_questions(analysis, difficulty_mix) -> list[Question]
generate_variants(paper, variant_count) -> list[PaperVariant]
generate_report_recommendations(result) -> list[str]
```

### 8.2 Structured Output Contract
Every Ollama call uses a system prompt that demands JSON-only output matching a fixed schema (provide the schema inline in the prompt). Example for chapter analysis:
```json
{
  "chapter_name": "string",
  "concepts": [{"name": "string", "bloom_level": "remember|understand|apply|analyze|evaluate|create"}],
  "learning_outcomes": ["string"],
  "competencies": [{"name": "string", "code": "string", "description": "string"}],
  "misconceptions": ["string"]
}
```

### 8.3 Validation & Retry
- Parse response as JSON; validate against a Pydantic model.
- On parse/validation failure: retry up to 2 times with a corrective system message ("Your last response was invalid JSON because X — return ONLY valid JSON matching the schema").
- If still failing after 3 attempts, fall back to the next model in the fallback chain (`gemma3:12b` → `llama3.1:8b`) before surfacing an error to the user.

### 8.4 Resilience
- Per-request timeout (e.g. 90s) with clear "still working" state in UI for long-running generation jobs.
- All AI calls run as background tasks (FastAPI `BackgroundTasks` or a simple job table) with a `GET /api/jobs/{id}` status endpoint — the UI polls rather than holding an open HTTP request.

---

## 9. Caching Strategy

- Hash uploaded PDF content (SHA-256). Store hash on `Chapter`.
- Before calling Ollama, check `AnalysisCache` for that hash; if present, reuse analysis and questions instead of regenerating.
- Cache is keyed on content, not filename, so re-uploads under a different name still hit the cache — this is what makes repeated demos fast and deterministic.

---

## 10. API Surface (representative, not exhaustive)

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/auth/login` | JWT login |
| POST | `/api/chapters/upload` | Upload chapter PDF + metadata |
| POST | `/api/chapters/{id}/analyze` | Trigger AI analysis (async job) |
| GET | `/api/jobs/{id}` | Poll job status |
| POST | `/api/chapters/{id}/generate-questions` | Trigger question generation (async job) |
| GET / PATCH / DELETE | `/api/questions/{id}` | Question Bank CRUD |
| POST | `/api/questions/bulk-action` | Approve/reject in bulk |
| POST | `/api/papers/generate` | Generate paper + variants |
| GET | `/api/papers/{id}/answer-key` | Download answer key PDF |
| POST | `/api/omr/generate` | Generate OMR sheets for an assessment |
| POST | `/api/omr/evaluate` | Upload + evaluate a scanned OMR sheet |
| GET | `/api/analytics/{level}/{id}` | Analytics by district/school/assessment/student |
| GET | `/api/reports/{type}/{id}` | Generate/fetch a report PDF |
| GET | `/api/dashboard` | Role-aware dashboard summary |

Swagger/OpenAPI docs auto-exposed at `/docs` (FastAPI default) — keep this on for the DEO demo, it doubles as live documentation.

---

## 11. Seed Data (for demos)

- 10 schools, 500 students across 3 grades, 3 subjects.
- 100 questions pre-generated and approved across difficulty/competency tags.
- 20 assessments with results already populated, so Analytics and Reports have something to show without running the full pipeline live.
- One "live" chapter left unanalyzed, specifically so the demo can show the real AI pipeline end-to-end on top of the seeded baseline.

---

## 12. Project Structure

```
backend/
  app/
  api/
  core/
  models/
  services/
  prompts/
  utils/
frontend/
  src/
    components/
    pages/
    features/
    hooks/
    services/
docker/
uploads/
reports/
models/        # Ollama model volume
database/
docs/
```

---

## 13. Docker Setup

- `Dockerfile.backend`, `Dockerfile.frontend`, Ollama via official image (no custom Dockerfile needed unless customizing model pull).
- `docker-compose.yml` defines all services + named volumes for: database file, `/uploads`, `/reports`, Ollama model cache.
- `docker compose up --build` must, on first run, pull the default Ollama model automatically (entrypoint script with `ollama pull qwen3:8b`) — don't make the user do this manually.
- All volumes must persist across `docker compose down` / `up` cycles (only `down -v` wipes them).

---

## 14. Documentation Deliverables

- `README.md` — quickstart, prerequisites, `docker compose up --build`, default credentials.
- Installation guide (incl. minimum RAM/VRAM for the default model — `qwen3:8b` is not trivial to run on CPU-only machines; document this honestly).
- API docs (link to `/docs`).
- Architecture diagram + DB schema diagram.
- Docker & Ollama setup guides.
- Developer guide (how to add a new question type, new report type, etc.).

---

## 15. Demo Flow (DEO presentation)

```
Login → Upload Chapter PDF → Extract Text → AI Analysis →
Review/Edit Competencies → Generate Questions → Review Question Bank →
Generate 30 Paper Variants → Generate OMR Sheets → Upload Filled OMR →
Automatic Evaluation → Analytics Dashboard → Generate Reports
```

**Demo-readiness checklist:**
- [ ] Seeded data makes Dashboard/Analytics look populated from second 1.
- [ ] The one "live" unanalyzed chapter proves the AI pipeline isn't smoke and mirrors.
- [ ] At least one pre-filled sample OMR image is bundled so the OMR evaluation step doesn't depend on printing/scanning during the live demo.
- [ ] Every async AI step shows a clear progress state — silence during a 30–60s LLM call reads as "broken" to a non-technical audience.

---

