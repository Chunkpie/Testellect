# 04 — Backend Specification

## Tech stack recap

Python 3.12, FastAPI, SQLAlchemy 2.x (async), Alembic, Pydantic v2, JWT auth (python-jose or PyJWT), OpenCV (`opencv-python-headless`), ReportLab.

## Project structure

```
backend/
├── app/
│   ├── main.py                 # FastAPI app factory, middleware, router registration
│   ├── core/
│   │   ├── config.py            # Pydantic Settings, env vars
│   │   ├── security.py          # JWT creation/validation, password hashing
│   │   ├── deps.py               # Shared FastAPI dependencies (get_db, get_current_user, require_role)
│   │   └── audit.py              # audit_log() helper used across all routers
│   ├── db/
│   │   ├── base.py                # SQLAlchemy Base, session factory
│   │   └── models/                # One file per table group (matches 03-database-schema.md sections)
│   ├── schemas/                   # Pydantic request/response models, mirrors models/ structure
│   ├── routers/
│   │   ├── auth.py
│   │   ├── schools.py
│   │   ├── students.py
│   │   ├── classes.py
│   │   ├── subjects.py
│   │   ├── books.py
│   │   ├── knowledge_base.py
│   │   ├── ai.py
│   │   ├── questions.py
│   │   ├── blueprints.py
│   │   ├── papers.py
│   │   ├── omr.py
│   │   ├── assessments.py
│   │   ├── reports.py
│   │   ├── analytics.py
│   │   ├── dashboard.py
│   │   ├── backup.py
│   │   └── audit.py
│   ├── services/                  # Business logic, one per domain, called by routers
│   │   ├── ai_pipeline/           # Document/Curriculum/Concept/Competency/Question agents — see 06
│   │   ├── question_engine.py
│   │   ├── paper_generator.py
│   │   ├── omr_engine.py
│   │   ├── analytics_engine.py
│   │   └── report_engine.py
│   ├── jobs/                       # Background job runner + job definitions
│   └── alembic/                     # Migrations
├── tests/
├── requirements.txt
└── Dockerfile
```

**Rule:** Routers contain no business logic — they validate input (via Pydantic), call a service function, and shape the response. All actual logic lives in `services/`. This keeps routers thin and testable services independently unit-testable (see `15-testing.md`).

## Service layer structure

Every FastAPI service listed in the project summary maps to a router + service pair:

| Service | Router file | Service file |
|---|---|---|
| Authentication | `routers/auth.py` | `core/security.py` + `services/auth_service.py` |
| Schools | `routers/schools.py` | `services/school_service.py` |
| Students | `routers/students.py` | `services/student_service.py` |
| Subjects | `routers/subjects.py` | `services/subject_service.py` |
| Books | `routers/books.py` | `services/book_service.py` |
| Knowledge Base | `routers/knowledge_base.py` | `services/ai_pipeline/*` |
| AI | `routers/ai.py` | `services/ai_pipeline/*`, `services/ai_assistant.py` |
| Questions | `routers/questions.py` | `services/question_engine.py` |
| Papers | `routers/papers.py` | `services/paper_generator.py` |
| OMR | `routers/omr.py` | `services/omr_engine.py` |
| Reports | `routers/reports.py` | `services/report_engine.py` |
| Analytics | `routers/analytics.py` | `services/analytics_engine.py` |
| Dashboard | `routers/dashboard.py` | aggregates analytics_engine + report_engine |
| Backup | `routers/backup.py` | `services/backup_service.py` |
| Audit Logging | `routers/audit.py` (read-only, admin) | `core/audit.py` (write path, called everywhere) |

## Cross-cutting middleware (applies to every request)

1. **JWT validation** — extracts and verifies bearer token, attaches `current_user` to request state. Public endpoints (`/auth/login`, `/health`) are explicitly exempted.
2. **Role validation** — `require_role(["administrator", "teacher"])` style dependency, used per-endpoint.
3. **School-scoping** — every query-building service function takes the current user's `school_id` and filters by it. DEO-role requests filter by `district_id` across schools instead. See `12-security.md` → "Authorization Model".
4. **Input validation** — Pydantic schemas reject malformed input before it reaches a service function.
5. **Audit logging** — any endpoint that creates/updates/deletes/approves/generates something calls `audit.log(...)` with action name, resource type/id, and a sanitized metadata dict, after the operation succeeds.

Implement 1–3 as FastAPI dependencies injected per-router (not global middleware) so public health/auth endpoints aren't entangled; implement 5 as an explicit call at the end of each mutating service function, not as blanket middleware, since audit entries need operation-specific detail.

## Background Jobs

The AI Pipeline (PDF processing, question generation) is long-running relative to an HTTP request and must not block it.

**v1 approach:** use FastAPI's `BackgroundTasks` for single-step async work, and a simple **in-process job table + polling worker loop** (a `jobs` table with `status`, `job_type`, `payload`, `result`, `error`, started as an `asyncio` task on app startup that polls for `pending` jobs) for the multi-stage AI Pipeline. This avoids adding Redis/Celery as a v1 dependency, consistent with the "single school PC, minimal moving parts" constraint in `01-project-overview.md`.

```python
# jobs/models.py (conceptual)
class Job(Base):
    id: int
    job_type: str          # "process_book", "generate_questions", "generate_paper", ...
    payload: dict           # JSON
    status: str              # pending, running, success, failed
    result: dict | None
    error: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
```

Each AI Pipeline stage is its own job row, so a failure at "extracting_concepts" doesn't require re-running "extracting_text," and the frontend's Live AI Progress UI can poll `books.processing_status` (denormalized from the latest job for that book) cheaply without joining the jobs table on every poll.

**Future scale-up note:** if district/state deployment later needs real concurrency/queueing guarantees, swap the in-process worker for Celery+Redis or RQ behind the same `jobs` table interface — service code that enqueues jobs shouldn't need to change, only the worker implementation.

## Error handling conventions

- Use FastAPI's `HTTPException` for all client-facing errors, with a consistent error body shape:
```json
{ "error": { "code": "QUESTION_NOT_FOUND", "message": "Question 123 not found", "details": {} } }
```
- Define an `AppError` base exception hierarchy in `core/errors.py` (e.g., `NotFoundError`, `ValidationError`, `AuthorizationError`, `AIProcessingError`) and a single FastAPI exception handler that converts these into the JSON shape above with the right HTTP status.
- Never leak stack traces or raw exception messages to the client in production mode (`DEBUG=false`); log them server-side instead.

## Configuration

All config via environment variables, loaded through Pydantic `Settings` (`core/config.py`), with sensible local-dev defaults and no secrets committed to the repo:

```
DATABASE_URL=sqlite:///./data/gseb.db
JWT_SECRET_KEY=<generated, see 12-security.md>
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=14
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=qwen3:8b
CHROMA_BASE_URL=http://chromadb:8001
FILE_STORAGE_PATH=/data/storage
BACKUP_PATH=/data/backups
ENVIRONMENT=production
DEBUG=false
```

## API versioning

All routes are mounted under `/api/v1`. Breaking changes get `/api/v2` mounted alongside, not an in-place break — relevant once district-level deployments mean multiple frontend versions could be talking to one backend during a rollout.

## Health and readiness

- `GET /health` — liveness, no auth, returns `{"status": "ok"}` if the process is up.
- `GET /health/ready` — readiness, checks DB connection, Ollama reachability, ChromaDB reachability; used by Docker healthchecks (see `14-docker-deployment.md`).

## Performance considerations for modest hardware

- Use async SQLAlchemy sessions and async HTTP calls to Ollama/ChromaDB (`httpx.AsyncClient`) so a slow LLM call doesn't block the event loop for unrelated requests.
- Set explicit timeouts on every Ollama call, with the AI Pipeline treating a timeout as a retryable failure (see `06-ai-engine.md` → "Timeouts and Retries"), not a crash.
- Paginate every list endpoint (`limit`/`offset` or cursor-based) — never return an unbounded list of students/questions/results.
- Cache expensive analytics aggregations in `analytics_cache` (see `03-database-schema.md`) with a sensible TTL (e.g., 1 hour) rather than recomputing on every dashboard load.
