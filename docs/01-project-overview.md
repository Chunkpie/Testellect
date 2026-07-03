# 01 — Project Overview

## What this is

The GSEB AI Assessment Platform is an offline-first, AI-assisted web application for Gujarat State Education Board (GSEB) schools, built to support **NAS (National Achievement Survey) and PARAKH-aligned competency-based assessments**.

It helps teachers create, manage, evaluate, and analyze assessments without internet access and without any paid AI API — all inference runs locally via Ollama.

## Who uses it

| Role | Primary needs |
|---|---|
| **Administrator** | School setup, user management, system configuration, backups |
| **Teacher** | Upload textbooks, build question banks, generate papers, scan OMR sheets, view student/class analytics |
| **Principal** | Compare classes and teachers within the school, view school-wide reports |
| **District Education Officer (DEO)** | Compare schools across the district, view district-wide competency trends |

## Problem being solved

Manually authoring competency-mapped, Bloom's-taxonomy-tagged, blueprint-compliant question papers is slow and inconsistent across teachers. Schools also lack tooling to evaluate OMR-based assessments and turn results into actionable, competency-level analytics (which students are weak in which competencies, not just which subjects).

This platform automates:

1. Turning uploaded textbook PDFs into a structured curriculum knowledge graph (concepts → learning outcomes → competencies).
2. Generating new, competency-tagged questions from that knowledge graph using a local LLM (Qwen3 8B via Ollama) — never directly from raw PDF text.
3. Letting teachers review/approve AI-generated questions before they enter a permanent, reusable question bank.
4. Assembling exam papers against a teacher-defined blueprint (marks distribution, Bloom distribution, competency distribution), producing multiple shuffled variants (Paper A/B/C…).
5. Generating and scanning OMR sheets (QR/barcode-identified) using OpenCV, automatically scoring them.
6. Producing competency-level analytics dashboards at student, class, school, and district level.

## What this explicitly is NOT

- It is **not** a cloud SaaS product. No tenant-hosted multi-school cloud deployment is in scope for v1.
- It does **not** call OpenAI, Anthropic, Google, or any other paid/hosted LLM API. Only Ollama, running locally.
- It does **not** auto-publish AI-generated content. A human approval step is mandatory before any AI-generated question reaches the live question bank.
- It is **not** a general LMS (no video lessons, no gradebook beyond assessment results, no parent portal in v1).

## Success criteria for v1 (single-school deployment)

A school should be able to:

- Run `docker compose up --build` on a single PC with no internet connection and have a working system.
- Onboard an Administrator, then Teachers, Students, and Classes.
- Upload a GSEB textbook PDF and have it processed into a browsable curriculum tree (Board → Grade → Subject → Unit → Chapter → Topic → Concept → Learning Outcome → Competency).
- Generate a batch of AI-drafted questions tagged with concept/competency/Bloom level/difficulty, and have a teacher approve/reject/edit them.
- Build an assessment blueprint and generate 2–3 paper variants from the approved question bank.
- Print OMR sheets, scan completed sheets (uploaded images), and get auto-scored results.
- View a Teacher Dashboard (student progress, weak concepts, competency performance) and a Principal Dashboard (class/teacher comparison).

## Languages

UI and content should support **English, Hindi, and Gujarati**, with Gujarati as a first-class citizen given GSEB's context — not bolted on later. See `05-frontend-specification.md` → "Internationalization" and `03-database-schema.md` for how multi-language text fields are modeled.

## Key technical decisions and why

| Decision | Why |
|---|---|
| FastAPI + SQLAlchemy + SQLite | Single-binary-feeling deployment, no external DB server required for v1, easy to containerize, async-friendly for AI calls |
| React + Vite + TypeScript | Modern, fast dev loop, large ecosystem, shadcn/ui gives a professional look without a design team |
| Ollama + Qwen3 8B | Fully local, no API costs, runs on modest hardware (designed against a baseline like a Lenovo LOQ-class laptop: 24GB RAM, RTX 3050 — see hardware note below), good enough quality for structured educational generation tasks when paired with strong prompting and RAG grounding |
| ChromaDB | Lightweight, embeddable, no separate server complexity beyond its own container, good enough for school-scale corpora (a few hundred textbook PDFs, not millions of documents) |
| Docker Compose | One-command install story for non-technical school IT staff |
| JWT + RBAC | Standard, well-understood, works well in an offline context (no dependency on an external identity provider) |

**Hardware baseline assumption:** the reference development/testing machine is a mid-range gaming/creator laptop class device (24GB RAM, RTX 3050, no dedicated server-grade GPU). All AI engine design (model size, batching, timeouts) should target hardware in this class or lower — assume some deployments will be CPU-only and degrade gracefully (slower generation, not failure).

## Glossary

- **NAS** — National Achievement Survey, India's large-scale competency-based learning assessment.
- **PARAKH** — Performance Assessment, Review, and Analysis of Knowledge for Holistic Development — India's national assessment body/framework that NAS aligns to.
- **Competency-based assessment** — Assessment designed around demonstrable learning outcomes/competencies rather than rote recall.
- **Bloom's Taxonomy** — Classification of cognitive learning levels (Remember, Understand, Apply, Analyze, Evaluate, Create) used to tag question difficulty/type.
- **Blueprint** — A teacher-defined specification for a paper: how many questions, what marks, what Bloom/competency/difficulty distribution.
- **OMR** — Optical Mark Recognition — scanning bubble sheets to extract answers.
- **Knowledge graph (in this project)** — The structured hierarchy Board → Grade → Subject → Unit → Chapter → Topic → Concept → Learning Outcome → Competency, plus the relationships between them, built once per uploaded textbook and reused thereafter.

## Relationship between this document and the others

This document is the "why." Everything downstream (`02` onward) is the "how." If a design decision in another document seems to contradict something here, this document wins — flag the conflict and resolve it in favor of the constraints above (offline-first, human-approval-gated AI, single-PC deployable).
