# 13 — API Reference

All endpoints are mounted under `/api/v1`. All responses use the error shape defined in `04-backend-specification.md` on failure. All list endpoints support `limit`/`offset` pagination unless noted. Auth: `Authorization: Bearer <access_token>` header required except where marked **Public**.

This reference defines the contract; exact request/response field names should mirror the Pydantic schemas an implementer derives from `03-database-schema.md`. Where this doc says "fields per schema," generate those fields directly from the corresponding table definition.

## Auth

| Method | Path | Roles | Description |
|---|---|---|---|
| POST | `/auth/login` | Public | `{email, password}` → `{access_token, refresh_token, user}` |
| POST | `/auth/refresh` | Public (valid refresh token required) | `{refresh_token}` → new `{access_token, refresh_token}` |
| POST | `/auth/logout` | Any | Revokes the presented refresh token |
| GET | `/auth/me` | Any | Returns current user profile |

## Schools

| Method | Path | Roles | Description |
|---|---|---|---|
| GET | `/schools` | deo, administrator | List schools (DEO: own district; administrator: own school only, returns single-item list) |
| GET | `/schools/{id}` | deo, administrator, principal | School detail |
| POST | `/schools` | deo | Create school (district onboarding flow) |
| PATCH | `/schools/{id}` | administrator, deo | Update school profile |

## Users / Settings: Users

| Method | Path | Roles | Description |
|---|---|---|---|
| GET | `/users` | administrator | List users in own school |
| POST | `/users` | administrator | Create user (teacher/principal account) |
| PATCH | `/users/{id}` | administrator | Update role/active status |
| DELETE | `/users/{id}` | administrator | Deactivate (soft) |

## Classes

| Method | Path | Roles | Description |
|---|---|---|---|
| GET | `/classes` | teacher, principal, administrator | List classes (teacher: assigned classes only, unless school setting grants broader visibility per `12-security.md`) |
| POST | `/classes` | administrator | Create class |
| PATCH | `/classes/{id}` | administrator | Update |
| DELETE | `/classes/{id}` | administrator | Soft delete |

## Students

| Method | Path | Roles | Description |
|---|---|---|---|
| GET | `/students` | teacher, principal, administrator | List, filterable by `class_id` |
| GET | `/students/{id}` | teacher, principal, administrator | Detail |
| POST | `/students` | administrator | Create |
| POST | `/students/bulk-import` | administrator | CSV/Excel bulk import |
| PATCH | `/students/{id}` | administrator | Update |
| DELETE | `/students/{id}` | administrator | Soft delete |

## Subjects

| Method | Path | Roles | Description |
|---|---|---|---|
| GET | `/subjects` | any authenticated | List, filterable by `grade` |
| POST | `/subjects` | administrator | Create (typically seeded, rarely manual) |

## Books

| Method | Path | Roles | Description |
|---|---|---|---|
| GET | `/books` | teacher, administrator | List, filterable by `grade`, `subject_id`, `processing_status` |
| GET | `/books/{id}` | teacher, administrator | Detail including `processing_status` |
| GET | `/books/{id}/status` | teacher, administrator | Lightweight polling endpoint, returns just status + current stage |
| POST | `/books` | teacher, administrator | Multipart upload; returns `202` immediately, processing runs async (per `04-backend-specification.md`) |
| POST | `/books/{id}/reprocess` | teacher, administrator | Re-run pipeline from Document Agent stage |
| POST | `/books/{id}/retry-stage` | teacher, administrator | Retry only a specific failed stage, `{stage: "extracting_concepts"}` |
| DELETE | `/books/{id}` | administrator | Soft delete; cascades per `07-rag-architecture.md` re-indexing notes |

## Knowledge Base

| Method | Path | Roles | Description |
|---|---|---|---|
| GET | `/knowledge-base/tree` | teacher, administrator | Full Board→Grade→Subject→Unit→Chapter→Topic→Concept→LO→Competency tree, filterable by `grade`/`subject_id` |
| GET | `/knowledge-base/search` | teacher, administrator | Semantic search, `?q=...&grade=...&subject_id=...`, queries ChromaDB per `07-rag-architecture.md` |
| GET | `/knowledge-base/concepts/{id}` | teacher, administrator | Concept detail incl. learning outcomes/competencies |
| PATCH | `/knowledge-base/concepts/{id}` | teacher, administrator | Manual correction of AI-extracted concept |
| GET | `/competencies` | any authenticated | List the seeded PARAKH competency taxonomy |

## AI

| Method | Path | Roles | Description |
|---|---|---|---|
| POST | `/ai/assistant/chat` | teacher | `{message, conversation_id?}` → assistant response, per `06-ai-engine.md` AI Teacher Assistant |
| POST | `/ai/generate-questions` | teacher | `{concept_id, competency_id?, bloom_level?, difficulty?, question_type?, count}` → enqueues generation job, returns `job_id` |
| GET | `/ai/jobs/{job_id}` | teacher, administrator | Poll job status/result |

## Question Bank

| Method | Path | Roles | Description |
|---|---|---|---|
| GET | `/questions` | teacher, administrator | List, filterable by `concept_id`, `competency_id`, `bloom_level`, `difficulty`, `approval_status`, `question_type` |
| GET | `/questions/{id}` | teacher, administrator | Detail incl. options |
| POST | `/questions` | teacher | Manual creation (Rich Question Editor, `generated_by='manual'`) |
| PATCH | `/questions/{id}` | teacher | Edit (text, options, tags) |
| POST | `/questions/{id}/approve` | teacher | Sets `approval_status='approved'` |
| POST | `/questions/{id}/reject` | teacher | Sets `approval_status='rejected'` |
| DELETE | `/questions/{id}` | administrator | Soft delete |

## Blueprints

| Method | Path | Roles | Description |
|---|---|---|---|
| GET | `/blueprints` | teacher, administrator | List |
| GET | `/blueprints/{id}` | teacher, administrator | Detail |
| POST | `/blueprints` | teacher | Create; server validates distributions sum correctly per `08-question-engine.md` |
| PATCH | `/blueprints/{id}` | teacher | Update (only if no papers generated yet from it, otherwise require a new blueprint) |
| POST | `/blueprints/{id}/check-coverage` | teacher | Dry-run the Selection Algorithm, returns shortfalls without generating a paper — lets the UI warn before committing |
| DELETE | `/blueprints/{id}` | teacher, administrator | Delete if unused |

## Papers

| Method | Path | Roles | Description |
|---|---|---|---|
| POST | `/papers/generate` | teacher | `{blueprint_id, variant_count}` → runs Selection Algorithm + renders PDFs, per `08-question-engine.md` |
| GET | `/papers` | teacher, administrator | List, filterable by `blueprint_id` |
| GET | `/papers/{id}` | teacher, administrator | Detail |
| GET | `/papers/{id}/download` | teacher, administrator | Streams the rendered PDF |
| DELETE | `/papers/{id}` | administrator | Delete |

## OMR

| Method | Path | Roles | Description |
|---|---|---|---|
| POST | `/omr/sheets/generate` | teacher | `{paper_id, class_id or student_ids[]}` → generates per-student or generic sheets per `09-omr-engine.md` |
| GET | `/omr/sheets/{id}/download` | teacher | Streams sheet PDF |
| POST | `/omr/scan` | teacher | Single image upload → scoring result |
| POST | `/omr/scan/batch` | teacher | Multiple image upload → per-sheet results |
| GET | `/omr/results/{id}` | teacher | Detail, incl. `needs_manual_review` flag |
| PATCH | `/omr/results/{id}/correct` | teacher | Manual correction of ambiguous bubbles |

## Assessments & Results

| Method | Path | Roles | Description |
|---|---|---|---|
| GET | `/assessments` | teacher, principal, administrator | List |
| POST | `/assessments` | teacher | Create (links blueprint + class + date) |
| PATCH | `/assessments/{id}` | teacher | Update status (`scheduled`→`conducted`→`scored`→`published`) |
| GET | `/assessments/{id}/results` | teacher, principal | List `student_results` for this assessment |
| POST | `/assessments/{id}/results/manual` | teacher | Manual marks entry (for short/long-answer portions, per `09-omr-engine.md`) |

## Reports

| Method | Path | Roles | Description |
|---|---|---|---|
| POST | `/reports/generate` | teacher, principal, deo | `{report_type, reference_id, date_range}` → enqueues render job |
| GET | `/reports` | teacher, principal, deo | List previously generated reports |
| GET | `/reports/{id}/download` | teacher, principal, deo | Streams PDF, ownership/scope checked |

## Analytics

| Method | Path | Roles | Description |
|---|---|---|---|
| GET | `/analytics/student/{id}` | teacher, principal | Per-student competency/score breakdown |
| GET | `/analytics/class/{id}` | teacher, principal | Per-class aggregates |
| GET | `/analytics/school/{id}` | principal, deo | Per-school aggregates |
| GET | `/analytics/district/{id}` | deo | Per-district aggregates |

## Dashboard

| Method | Path | Roles | Description |
|---|---|---|---|
| GET | `/dashboard` | any authenticated | Returns the role-appropriate composite dashboard payload (backend decides shape by role, per `11-analytics-engine.md`) |

## Backup

| Method | Path | Roles | Description |
|---|---|---|---|
| POST | `/backup` | administrator | Trigger backup, `{backup_type}` |
| GET | `/backup` | administrator | List past backups |
| GET | `/backup/{id}/download` | administrator | Download backup archive |
| POST | `/backup/{id}/restore` | administrator | Restore from backup (destructive, requires confirmation flag in body) |

## Audit

| Method | Path | Roles | Description |
|---|---|---|---|
| GET | `/audit-logs` | administrator, deo | List, filterable by `action`, `user_id`, date range, scoped per `12-security.md` |

## Health

| Method | Path | Roles | Description |
|---|---|---|---|
| GET | `/health` | Public | Liveness |
| GET | `/health/ready` | Public | Readiness (DB/Ollama/ChromaDB checks) |

## Conventions for an implementer

- Every `POST`/`PATCH` request body schema should be derivable directly from the corresponding table in `03-database-schema.md`, minus server-controlled fields (`id`, `created_at`, `approved_by`, etc.).
- Every list endpoint returns `{items: [...], total: number, limit: number, offset: number}`.
- Long-running operations (book processing, question generation, report generation, paper generation with many variants) return `202 Accepted` with a job/resource id immediately, never block the request — consistent with `04-backend-specification.md` → "Background Jobs".
