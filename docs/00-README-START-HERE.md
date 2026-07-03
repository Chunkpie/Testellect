# GSEB AI Assessment Platform — Documentation Index

**START HERE.** This folder contains the complete specification for building the GSEB AI Assessment Platform (NAS/PARAKH competency-based assessment system). It is written to be handed directly to an AI coding agent (e.g., Claude Code, Cursor, or a similar tool) as the source of truth for implementation.

## How to use this documentation set (for an AI agent)

If you are an AI agent tasked with building this project from these docs, follow this order:

1. Read **01-project-overview.md** first for the big picture, goals, and constraints.
2. Read **02-system-architecture.md** to understand how components fit together.
3. Read **03-database-schema.md** before writing any backend code — almost everything depends on the data model.
4. Read **04-backend-specification.md** and **13-api-reference.md** together when building FastAPI services.
5. Read **05-frontend-specification.md** and **18-ui-guidelines.md** together when building the React app.
6. Read **06-ai-engine.md** and **07-rag-architecture.md** before touching anything Ollama/ChromaDB related.
7. Read **08-question-engine.md**, **09-omr-engine.md**, **10-report-engine.md**, **11-analytics-engine.md** as you reach those modules.
8. Read **12-security.md** continuously — apply it to every module, not just once.
9. Read **14-docker-deployment.md** when wiring up `docker compose`.
10. Read **15-testing.md** to know what "done" means for each module.
11. Read **16-installation.md** is the end-user-facing setup guide — keep it in sync with actual `docker compose` behavior as you build.
12. Read **17-developer-guide.md** for local dev workflow (non-Docker).
13. Read **19-roadmap.md** for phase sequencing — **build in phase order, not module order.**
14. Read **20-ai-prompt-library.md** when implementing any LLM-calling code — use these prompts verbatim as starting points, don't improvise new ones.

## Build order (do not skip ahead)

This mirrors the Development Plan phases in `19-roadmap.md`. Each phase should result in a runnable, testable increment.

| Phase | What gets built | Docs to use |
|---|---|---|
| 1 | Repo scaffold, Docker Compose skeleton, JWT auth | 02, 03 (users table), 04, 12, 14 |
| 2 | Full DB schema, School/Student/Class CRUD | 03, 04, 13 |
| 3 | PDF upload, text extraction, ChromaDB ingestion, curriculum knowledge graph | 03, 06, 07 |
| 4 | Question generation + validation pipeline, Question Bank UI | 06, 07, 08, 20 |
| 5 | Blueprint Builder, Paper Generator (Paper A/B/C variants) | 08, 13 |
| 6 | OMR sheet generation + OpenCV scanning pipeline | 09 |
| 7 | Reports + Dashboards (Teacher/Principal/DEO) | 10, 11 |
| 8 | Hardening, tests, docs, production packaging | 12, 14, 15, 16 |

## Non-negotiable constraints (apply to every phase)

- **Fully offline.** No call in the codebase may require internet access at runtime. No paid AI APIs. All AI inference goes through local Ollama.
- **Local-first hardware.** Must run on a single school PC via `docker compose up --build`. Assume modest hardware (no GPU guaranteed).
- **SQLite first.** Use SQLAlchemy in a way that makes a future Postgres swap a configuration change, not a rewrite (see `03-database-schema.md` → "Future Postgres Migration").
- **Every AI-generated question is provisional** until a human teacher approves it. Never auto-publish AI output into the live question bank.
- **Audit everything.** Every state-changing API call must write an audit log entry (see `12-security.md`).
- **Multi-tenancy by school**, designed for single-school deployment today, district/state tomorrow. Don't hardcode single-school assumptions into schema or auth.

## Repository layout this documentation assumes

```
gseb-platform/
├── backend/              # FastAPI app (see 04-backend-specification.md)
├── frontend/             # React + Vite app (see 05-frontend-specification.md)
├── ai-engine/            # Ollama prompt templates, agent pipeline (see 06, 20)
├── docker/               # Dockerfiles per service
├── docker-compose.yml    # See 14-docker-deployment.md
├── docs/                 # This documentation set, kept in the repo
├── scripts/              # Setup/backup/migration scripts
└── tests/                # See 15-testing.md
```

## Document list

01. Project Overview
02. System Architecture
03. Database Schema
04. Backend Specification
05. Frontend Specification
06. AI Engine
07. RAG Architecture
08. Question Engine
09. OMR Engine
10. Report Engine
11. Analytics Engine
12. Security
13. API Reference
14. Docker Deployment
15. Testing
16. Installation
17. Developer Guide
18. UI Guidelines
19. Roadmap
20. AI Prompt Library

## A note on scope vs. the original summary doc

The source project summary (GSEB AI Assessment Platform – Project Summary) described an eventual 120,000–180,000 word, 400–600 page documentation set. This documentation set is intentionally **dense and complete enough to build from**, but is not artificially padded to hit a word count. Every section here is meant to be read and acted on, not skimmed. If you need more depth in any one area as you build, extend that specific document rather than inflating all of them.
