# 05 — Frontend Specification

## Tech stack recap

React 19, TypeScript, Vite, TailwindCSS, shadcn/ui, TanStack Query, Zustand, React Hook Form, Zod.

## Project structure

```
frontend/
├── src/
│   ├── main.tsx
│   ├── App.tsx                  # Router setup
│   ├── api/                      # Typed API client functions, one file per backend router
│   │   ├── client.ts              # Axios/fetch wrapper with auth header injection, refresh logic
│   │   ├── books.ts
│   │   ├── questions.ts
│   │   ├── papers.ts
│   │   ├── omr.ts
│   │   ├── analytics.ts
│   │   └── ...
│   ├── stores/                    # Zustand stores
│   │   ├── authStore.ts
│   │   ├── uiStore.ts             # sidebar collapsed, dark mode, etc.
│   │   └── uploadProgressStore.ts
│   ├── hooks/                      # TanStack Query hooks wrapping api/ functions
│   │   ├── useBooks.ts
│   │   ├── useQuestionBank.ts
│   │   └── ...
│   ├── components/
│   │   ├── ui/                     # shadcn/ui primitives (generated via shadcn CLI, not hand-rolled)
│   │   ├── layout/                 # Sidebar, Topbar, AppShell
│   │   └── shared/                 # Reusable domain components (QuestionCard, CompetencyBadge, etc.)
│   ├── modules/                     # One folder per the 10 frontend modules (see below)
│   │   ├── dashboard/
│   │   ├── books/
│   │   ├── knowledge-base/
│   │   ├── question-bank/
│   │   ├── blueprint-builder/
│   │   ├── paper-generator/
│   │   ├── omr/
│   │   ├── reports/
│   │   ├── analytics/
│   │   └── settings/
│   ├── i18n/                        # Translation resource bundles
│   │   ├── en.json
│   │   ├── hi.json
│   │   └── gu.json
│   ├── lib/                          # Pure utility functions
│   ├── types/                        # Shared TS types, mirrors backend Pydantic schemas
│   └── styles/
├── index.html
├── vite.config.ts
├── tailwind.config.ts
└── package.json
```

## Modules (mapped to project summary's frontend module list)

### Dashboard
Role-aware landing page. Renders a different layout per role (Administrator/Teacher/Principal/DEO) by composing shared widgets (`StatCard`, `TrendChart`, `WeakConceptsList`) rather than four separate hand-built pages — see `11-analytics-engine.md` for what each role's dashboard actually shows.

### Books
Upload UI (drag-and-drop, see "Drag-and-drop uploads" below), book list with `processing_status` badges, and the **Live AI Progress** view: a per-book detail page that polls `GET /api/v1/books/{id}` every few seconds while status is not `ready`/`failed_*`, rendering the pipeline stages (Document Agent → Curriculum Agent → Concept Extraction → Competency Mapping) as a step indicator.

### Knowledge Base
Browsable tree view (Board → Grade → Subject → Unit → Chapter → Topic → Concept → Learning Outcome → Competency) using a collapsible tree component. Includes **Semantic Search** — a search box that calls a backend endpoint which queries ChromaDB and returns matching chunks/concepts, not naive string matching.

### Question Bank
The **Rich Question Editor** lives here: a form supporting MCQ (with option management + correct-answer marking), short/long answer, true/false, and fill-in-the-blank question types, with fields for concept/competency/Bloom level/difficulty/marks tagging. Also includes the review queue (filter by `approval_status=pending_review`) where teachers approve/reject/edit AI-generated questions — this is the human-in-the-loop gate described in `01-project-overview.md` and must be visually unambiguous (e.g., a clear "AI-generated, unreviewed" badge) so teachers never confuse draft and approved content.

### Blueprint Builder
Form-driven UI for defining a blueprint: grade/subject/chapter multi-select, total questions/marks, and three distribution editors (difficulty, Bloom, competency) implemented as either sliders that must sum to 100% or explicit count inputs that must sum to `total_questions` — validate client-side with Zod before submit, and surface the same validation server-side (never trust client validation alone).

### Paper Generator
Triggers generation against a blueprint, shows generated variants (Paper A/B/C…) with PDF preview/download links, and a regenerate option if the teacher wants different randomization.

### OMR
Two sub-flows: (1) generate/print OMR sheets for a paper+class, showing the QR/barcode-bearing sheet preview; (2) upload scanned sheet images (single or batch) and show scoring results, flagging any `needs_manual_review` results from low OpenCV confidence for a manual correction UI.

### Reports
Generate and download student/class/school/district PDF reports (via `10-report-engine.md`'s ReportLab templates), with a history list of previously generated reports.

### Analytics
Interactive dashboards (charts via a charting library — Recharts is a reasonable default given React 19 compatibility) for Teacher/Principal/DEO views per `11-analytics-engine.md`.

### Settings
School profile, user management (Administrator only), language preference, backup management (Administrator only — triggers `14-docker-deployment.md`/backup service flows).

## Internationalization

- UI chrome (buttons, labels, nav) uses `react-i18next` (or equivalent) with `en.json`/`hi.json`/`gu.json` resource bundles under `src/i18n/`.
- User's `preferred_language` (from `users` table) sets the initial locale on login; a language switcher in the topbar allows runtime switching.
- Domain content (question text, etc.) is **not** run through the i18n library — it's rendered directly from whichever `_en`/`_hi`/`_gu` column matches the active locale, falling back to `_en` if the localized field is empty (per `03-database-schema.md`).
- Gujarati font rendering: ensure the chosen UI font stack includes proper Gujarati glyph support (e.g., pair a Latin font with `Noto Sans Gujarat` as a fallback) — don't assume a Western font stack renders Gujarati correctly by default.

## State management split

- **TanStack Query** owns all server state (anything that comes from the API) — books, questions, papers, results, analytics. Never duplicate this into Zustand.
- **Zustand** owns client-only UI state — current sidebar collapse state, theme (dark/light), in-progress upload tracking, multi-step form wizard state (e.g., Blueprint Builder's current step) before submission.
- **React Hook Form + Zod** own all form state and validation, for every form in the app — don't hand-roll form state with `useState`.

## Design direction

See `18-ui-guidelines.md` for the full visual language (inspired by Linear/Vercel/Notion/Stripe per the project summary) — this document covers structure, not visual styling.

## Drag-and-drop uploads

Implement with a small, focused library (e.g., `react-dropzone`) rather than hand-rolling drag event handlers. Show per-file progress (use `XMLHttpRequest` or `fetch` with a `ReadableStream`/`axios` `onUploadProgress` to get real progress, not a fake spinner) and surface backend validation errors (file too large, wrong type) inline per file.

## Routing structure (React Router, conceptual)

```
/login
/dashboard
/books                 /books/:id
/knowledge-base
/question-bank         /question-bank/review-queue
/blueprints            /blueprints/:id
/papers                /papers/:id
/omr/generate          /omr/scan
/reports
/analytics/teacher     /analytics/principal     /analytics/deo
/settings/profile      /settings/users     /settings/backups
```

Route guards check `authStore`'s current user role against each route's allowed roles (e.g., `/settings/users` is Administrator-only); unauthorized access redirects to `/dashboard` with a toast, not a blank page.

## API client conventions

- Single `client.ts` Axios instance with a request interceptor injecting the JWT access token and a response interceptor that, on `401`, attempts a silent refresh via the refresh token once before forcing logout.
- Every `api/*.ts` file exports plain typed async functions (`getBooks()`, `createQuestion()`, etc.) — no React-specific code in `api/`. `hooks/*.ts` wraps these in `useQuery`/`useMutation`, which is where cache invalidation keys live (e.g., approving a question invalidates the `question-bank` query key).
