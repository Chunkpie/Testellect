# 02 — System Architecture

## High-level component diagram (textual)

```
┌─────────────────────────────────────────────────────────────────┐
│                         Single School PC                        │
│                                                                   │
│  ┌──────────────┐      ┌──────────────────┐                     │
│  │   React       │ ───▶ │   FastAPI         │                     │
│  │   Frontend    │ ◀─── │   Backend         │                     │
│  │  (Vite, :5173 │      │   (:8000)         │                     │
│  │   or served   │      │                   │                     │
│  │   by Nginx)   │      └─────────┬─────────┘                     │
│  └──────────────┘                 │                               │
│                                    │ SQLAlchemy                   │
│                          ┌─────────▼─────────┐                    │
│                          │   SQLite           │                    │
│                          │   (volume-mounted) │                    │
│                          └────────────────────┘                    │
│                                    │                                │
│                          ┌─────────▼─────────┐    ┌──────────────┐ │
│                          │   ChromaDB         │    │   Ollama     │ │
│                          │   (:8001, vector   │◀──▶│   (:11434)   │ │
│                          │   embeddings)      │    │   Qwen3 8B   │ │
│                          └────────────────────┘    └──────────────┘ │
│                                    │                                │
│                          ┌─────────▼─────────┐                     │
│                          │  Shared File       │                     │
│                          │  Storage (volume)  │                     │
│                          │  PDFs/Papers/OMR/  │                     │
│                          │  Backups           │                     │
│                          └────────────────────┘                     │
└───────────────────────────────────────────────────────────────────┘
```

All six logical pieces (Frontend, Backend, SQLite, ChromaDB, Ollama, Shared Storage) run as Docker containers/volumes on one machine, per `14-docker-deployment.md`. There is no required external network call anywhere in this diagram.

## Service responsibilities

### Frontend (React + Vite + TypeScript)
- Renders all role-specific dashboards and modules.
- Talks **only** to the FastAPI backend over HTTP/JSON (never directly to Ollama or ChromaDB).
- Holds no business logic beyond form validation and optimistic UI state (via TanStack Query + Zustand).

### Backend (FastAPI)
- Single source of truth for business logic, authorization, and orchestration.
- Owns the SQLite database via SQLAlchemy/Alembic.
- Is the only service that talks to Ollama and ChromaDB.
- Exposes REST endpoints documented in `13-api-reference.md`.
- Runs the AI Pipeline (see below) as a set of orchestrated, independently-retryable agent steps — not one giant LLM call.

### Ollama (local LLM runtime)
- Hosts Qwen3 8B.
- Receives structured prompts from the backend's AI Engine (see `06-ai-engine.md`, `20-ai-prompt-library.md`).
- Stateless from the app's perspective — every call carries full context needed.

### ChromaDB (vector store)
- Stores chunk embeddings for uploaded curriculum documents.
- Powers semantic search and RAG retrieval for question generation and the AI Teacher Assistant.

### SQLite
- System of record for all structured, relational data (users, schools, students, questions, papers, results, audit logs — full list in `03-database-schema.md`).
- Mounted as a Docker volume so data survives container rebuilds.

### Shared File Storage
- A Docker volume mounted into the backend container, holding uploaded PDFs, generated papers, OMR sheet images/PDFs, generated reports, and backup archives.
- Never accessed directly by the frontend; always served through authenticated backend endpoints.

## The AI Pipeline as an architectural pattern

This is the most important architectural idea in the system, repeated from the project summary because it governs how the AI Engine, RAG Architecture, and Question Engine docs are all structured:

```
PDF Upload
   │
   ▼
Document Agent           — extract raw text from PDF (PyPDF2/pdfplumber), basic cleanup
   │
   ▼
Curriculum Agent         — segment into Unit/Chapter/Topic structure using headings + LLM assist
   │
   ▼
Concept Extraction Agent — pull out discrete concepts per topic (LLM, RAG-grounded)
   │
   ▼
Competency Mapping Agent — map concepts to learning outcomes + competencies (LLM + curriculum knowledge base)
   │
   ▼
Question Generation Agent — generate candidate questions per concept/competency/Bloom level (LLM, RAG-grounded)
   │
   ▼
Question Validation Agent — automatic quality scoring (see Question Intelligence Engine in 08)
   │
   ▼
Question Bank            — questions land here as "pending_review", never auto-approved
   │
   ▼
Blueprint Engine          — teacher defines distribution requirements
   │
   ▼
Paper Generator            — assembles Paper A/B/C from approved bank against blueprint
   │
   ▼
OMR Generator               — produces printable OMR sheets w/ QR+barcode identifiers
   │
   ▼
Reports                    — scanned results flow into analytics
```

**Architectural rule:** every stage above is implemented as its own service/module with its own input validation, its own error handling, and its own retry logic. A failure in Question Generation must never corrupt or block Curriculum Agent output that's already been committed. Each stage reads its input from the database/vector store (not from in-memory state passed from the previous stage), so any stage can be re-run independently. See `06-ai-engine.md` → "Agent Pipeline Contracts" for the exact interface each agent must implement.

## Request flow example: "Teacher uploads a textbook PDF"

1. Frontend `POST /api/v1/books` (multipart upload) → Backend.
2. Backend validates file (size/type), persists to Shared File Storage, writes a `books` row with status `uploaded`, returns `202 Accepted` with a `book_id` and `processing_status` immediately — **does not block the HTTP request on AI processing.**
3. Backend enqueues a background task (FastAPI `BackgroundTasks` or a simple in-process job queue — see `04-backend-specification.md` → "Background Jobs") that runs the Document Agent → Curriculum Agent → Concept Extraction Agent → Competency Mapping Agent chain.
4. Each agent step updates `books.processing_status` (e.g., `extracting_text`, `building_curriculum`, `extracting_concepts`, `mapping_competencies`, `ready`, or `failed_at_<stage>`).
5. Frontend polls `GET /api/v1/books/{id}` (or a lightweight `GET /api/v1/books/{id}/status`) to show live progress ("Live AI Progress" UI module from `05-frontend-specification.md`).
6. On `ready`, the curriculum tree becomes browsable and question generation becomes available for that book.

## Request flow example: "Teacher generates a paper"

1. Teacher fills Blueprint Builder UI → `POST /api/v1/blueprints`.
2. Teacher triggers `POST /api/v1/papers/generate` with `blueprint_id` and `variant_count`.
3. Backend's Paper Generator selects approved questions from the Question Bank matching the blueprint's distribution constraints (see `08-question-engine.md` → "Selection Algorithm"), builds N variants with shuffled question/option order, writes `papers` + `paper_questions` rows.
4. Backend renders each paper to PDF (ReportLab) and stores in Shared File Storage; returns download links.
5. Optionally, teacher requests OMR sheets for the same papers → `09-omr-engine.md` pipeline.

## Multi-tenancy model

Every table that holds school-specific data carries a `school_id` foreign key (see `03-database-schema.md`). Even though v1 ships for a single school per deployment, this is non-negotiable groundwork for district/state deployments in `19-roadmap.md`. Authorization middleware (see `12-security.md`) scopes every query to the requesting user's `school_id`, except for DEO-role users, who are explicitly scoped to "all schools in their district."

## Internationalization architecture

Translatable content (question text, options, UI strings) is stored using a **language-suffixed column pattern** for structured content (e.g., `question_text_en`, `question_text_hi`, `question_text_gu`) rather than a separate translations table, to keep question retrieval simple and fast. UI chrome strings (buttons, labels) use a standard i18n JSON resource bundle per language on the frontend (`react-i18next` or equivalent). See `05-frontend-specification.md` → "Internationalization" for the frontend half of this.

## Why not microservices-over-network for AI agents

Each "agent" in the AI Pipeline is a Python module/class inside the FastAPI backend process, not a separate networked microservice. This is intentional: school hardware is resource-constrained, and the overhead of multiple networked services for what is fundamentally a sequence of LLM calls and DB writes would add operational fragility (more containers, more failure points) without a corresponding benefit at this scale. Ollama and ChromaDB are the only separate service boundaries, because they have genuinely different runtime/resource profiles (GPU-aware inference, vector indexing) that benefit from isolation.

## Future architecture notes (do not build now, but don't preclude)

- District/state deployment: same architecture, but backend points at a shared Postgres instance instead of per-school SQLite, and a school-selector replaces the implicit single-school context. See `03-database-schema.md` → "Future Postgres Migration" and `19-roadmap.md`.
- Cloud sync: an optional, explicitly opt-in background sync service that pushes anonymized/aggregated analytics upward — never raw student PII — would be a separate service added later, not a retrofit of the offline core.
