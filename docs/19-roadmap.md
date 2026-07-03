# 19 — Roadmap

## Development Plan (v1, single-school deployment)

This mirrors and expands the project summary's phase list. **Build in this order** — later phases depend on earlier ones being genuinely functional, not just stubbed.

### Phase 1 — Project setup, Docker, Authentication
- Repo scaffold per `04-backend-specification.md`/`05-frontend-specification.md` structure.
- `docker-compose.yml` skeleton (backend + frontend + SQLite volume only at first; Ollama/ChromaDB added in Phase 3 when actually needed, to keep early iteration fast).
- `users`/`schools`/`districts`/`refresh_tokens` tables, JWT auth, RBAC middleware skeleton (`12-security.md`).
- **Exit criteria**: can log in as a seeded administrator account and hit a protected `/auth/me` endpoint successfully; role-based 403s work correctly.

### Phase 2 — Database, School Management, Student Management
- Full schema from `03-database-schema.md` (all tables, even ones not used until later phases — get the schema right once).
- Classes/Students/Subjects CRUD + UI (Students module, bulk import).
- **Exit criteria**: an administrator can fully set up a school's class/student roster through the UI alone, no manual DB work.

### Phase 3 — PDF Upload, Knowledge Base, AI Curriculum Engine
- Add Ollama + ChromaDB containers.
- Document Agent, Curriculum Agent, Concept Extraction Agent, Competency Mapping Agent (`06-ai-engine.md`).
- **Blocker to resolve first**: source and seed the actual PARAKH/NAS competency taxonomy (`07-rag-architecture.md` → "Seeding the Competency Taxonomy") — do not proceed to Competency Mapping Agent implementation without this reference data in place.
- Knowledge Base browsing UI + semantic search.
- **Exit criteria**: upload a real GSEB textbook PDF, watch it process through to `ready`, and browse a sensible (spot-checked by a human) curriculum tree for it.

### Phase 4 — Question Generation, Question Bank
- Question Generation Agent + Question Validation Agent (`06`, `08-question-engine.md`).
- Rich Question Editor + Review Queue UI.
- **Exit criteria**: generate a batch of questions for a real concept, have a human reviewer approve/reject/edit them through the UI, confirm only approved questions are queryable as such.

### Phase 5 — Blueprint Builder, Paper Generator
- Blueprint CRUD + distribution validation.
- Selection Algorithm + multi-variant paper generation + PDF rendering (`08-question-engine.md`).
- **Exit criteria**: build a blueprint, generate 3 paper variants from real approved questions, confirm each variant has correctly shuffled question/option order and downloadable PDFs.

### Phase 6 — OMR Engine
- OMR sheet generation (QR/barcode + bubble grid PDF rendering).
- OpenCV scanning pipeline (`09-omr-engine.md`).
- **Exit criteria**: pass all 9 OMR test scenarios from `15-testing.md` → "OMR Engine Test Cases", including the synthetic-fixture automated tests.

### Phase 7 — Reports, Analytics
- `analytics_engine.py` aggregations + `competency_results` computation (`11-analytics-engine.md`).
- `report_engine.py` PDF generation (`10-report-engine.md`).
- Teacher/Principal/DEO dashboards.
- **Exit criteria**: run a full assessment through scoring, confirm competency-level analytics populate correctly and a class report PDF generates with accurate data.

### Phase 8 — Testing, Documentation, Production Packaging
- Full test suite per `15-testing.md` passing.
- Security hardening pass against `12-security.md` checklist.
- Production `docker-compose.yml` (TLS, resource limits, non-root containers per `14-docker-deployment.md`).
- Finalize `16-installation.md` against the actual built system (re-walk every step as a fresh user would).
- **Exit criteria**: a non-developer can follow `16-installation.md` start to finish on a clean machine and end up with a working system.

## Post-v1 roadmap (future phases, not built now)

These are explicitly **out of scope for v1** but the architecture should not preclude them (see `02-system-architecture.md` → "Future architecture notes" and `03-database-schema.md` → "Future Postgres Migration"):

- **Multi-school deployment**: one backend instance serving multiple schools' data with proper tenant isolation (schema already supports `school_id` scoping; this phase is about deployment topology and admin tooling for managing multiple schools from one install).
- **District servers**: a district-level deployment aggregating multiple school instances' data, likely via the opt-in sync service described below rather than direct shared-database access (preserves each school's offline autonomy).
- **State-level deployment**: aggregation one level up from district, same pattern.
- **ERP integration**: connecting to existing school/state ERP systems for roster sync, avoiding duplicate manual data entry — requires defining an integration contract once specific target ERPs are known.
- **Cloud synchronization**: strictly opt-in, aggregate/anonymized analytics sync upward (never raw student PII), as a separate add-on service.
- **Full NAS/PARAKH alignment certification**: deeper validation that the competency taxonomy and assessment methodology meet whatever formal PARAKH alignment review process exists, beyond this project's own internal competency-tagging.
- **Predictive analytics** (explicitly deferred per `11-analytics-engine.md` — would need its own data-sufficiency and validation plan before being trustworthy).

## Sequencing principle

Do not let polish work on later-phase features (e.g., advanced analytics charts) start before earlier-phase exit criteria are genuinely met. A common failure mode in projects like this is front-loading UI polish on flashy AI features while auth/security/data-integrity foundations stay half-finished — the phase order above exists specifically to prevent that.
