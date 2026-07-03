# 15 — Testing

## Testing philosophy

Given the AI-pipeline-heavy nature of this system, testing splits into two very different categories that need different strategies: **deterministic logic** (auth, CRUD, selection algorithms, OMR geometry) which should have thorough automated tests, and **AI-output-dependent logic** (question generation quality, concept extraction accuracy) which needs a mix of automated structural checks (did we get valid JSON in the right shape) plus periodic manual/human-reviewed spot-checks, since LLM output quality isn't something a simple `assert` can fully capture.

## Backend testing

- **Framework**: `pytest` + `pytest-asyncio` for async FastAPI routes, `httpx.AsyncClient` for endpoint-level tests against the app.
- **Test database**: a fresh SQLite file (or in-memory SQLite) per test session, with Alembic migrations applied, never the dev/prod database.
- **Layers to test**:
  - **Unit tests** for `services/` functions in isolation (e.g., `select_questions_for_blueprint` given a fixed set of fixture questions — this is exactly the kind of deterministic logic in `08-question-engine.md` that needs rigorous coverage, since a bug here silently produces wrong exam papers).
  - **Integration tests** for routers, hitting real endpoints with a test client, verifying status codes, response shapes, and authorization (a teacher token must get `403` on administrator-only endpoints, etc. — explicitly test the negative cases from `12-security.md`, not just the happy path).
  - **AI pipeline tests** mock the Ollama client (don't call a real LLM in CI — too slow, non-deterministic, and CI likely has no GPU). Test that each agent correctly parses a given mocked LLM JSON response into the right DB rows, and correctly handles a malformed/timeout response per the retry logic in `06-ai-engine.md`.

### Required test scenarios by module

| Module | Must-test scenarios |
|---|---|
| Auth | Login success/failure, token refresh, token expiry, role-based 403s, rate limiting on repeated failed logins |
| Students/Classes | CRUD, school-scoping (school A's teacher cannot see school B's students), soft-delete behavior |
| Books | Upload validation (rejects non-PDF, rejects oversized file), status transitions, retry-single-failed-stage behavior |
| Question Engine | Selection algorithm with exact-fit bank, with shortfall, with zero matches; duplicate scoring; approval gate (unapproved questions never selectable) |
| Blueprint/Paper | Distribution validation (percentages summing correctly), variant generation produces distinct option orders per variant |
| OMR Engine | See "OMR Engine Test Cases" below |
| Analytics | Mastery level thresholds at boundary values (39% vs 40% vs 64% vs 65%), minimum sample size gating |
| Security/Audit | Every mutating endpoint produces exactly one expected audit log entry with correct `action`/`resource_id` |

## OMR Engine Test Cases

Per `09-omr-engine.md`, build a fixture set of test sheet images covering:

1. A perfectly scanned, well-lit, straight sheet (baseline — must score 100% correctly).
2. A sheet photographed at a slight rotation (~5–10°) — perspective correction must still register correctly.
3. A sheet with uneven lighting (a shadow across part of the sheet) — fill detection must not misread shadowed-but-unfilled bubbles as filled.
4. A sheet with a stray pencil mark near (but not in) a bubble — must not register as a fill.
5. A sheet with an erased-but-still-faintly-visible mark — should fall below the fill threshold, not register as ambiguous unless genuinely borderline.
6. A sheet with a deliberately double-marked question — must be flagged `AMBIGUOUS`, not silently pick one.
7. A sheet with a blank (unanswered) question — must be recorded as unanswered, not as incorrect-but-ambiguous, and must not crash the pipeline.
8. A sheet where fewer than 3 corner markers are detectable (e.g., a corner is torn/obscured) — must fail cleanly with a clear "rescan" error, not produce a corrupted/garbage result silently.
9. A batch upload containing a mix of the above — verify one bad sheet doesn't abort processing of the others.

Each of these should be an automated test once a representative fixture image exists (generate synthetic ones programmatically with OpenCV/PIL by drawing a sheet from the layout config and rendering controlled "filled" bubbles, rather than relying solely on physically scanned photos for the unit test suite — keep a smaller set of *real* scanned photos as a separate manual/periodic validation set, since synthetic and real-world camera artifacts won't be identical).

## Frontend testing

- **Component tests**: Vitest + React Testing Library for individual components (forms validate correctly, QuestionCard renders the right badge for `pending_review` vs `approved`, etc.).
- **E2E tests**: Playwright for critical user flows end-to-end against a real (test) backend:
  - Login → upload book → see processing status progress → book reaches `ready`.
  - Generate questions → review queue shows them → approve one → it appears in question bank as approved.
  - Build blueprint → generate paper → download PDF succeeds.
  - Upload OMR scan → see scored result.
- Don't aim for 100% E2E coverage of every module — pick the handful of flows above that represent the core value chain end-to-end, and rely on component/unit tests for breadth elsewhere.

## AI output quality spot-checks (manual, periodic)

Not automatable as pass/fail, but should be a defined, repeated process (e.g., before each release, and after any prompt template change in `20-ai-prompt-library.md`):

1. Pick 2–3 chapters from different subjects/grades already in the system.
2. Generate a batch of questions for each.
3. Have an actual teacher (or someone with subject knowledge) review: are these factually correct, appropriately difficulty-tagged, and genuinely testing the stated competency?
4. Track a rough "looked fine without edits" / "needed minor edit" / "wrong, rejected" ratio over time as a quality signal — a regression in this ratio after a prompt change is a real signal worth investigating, even without a formal benchmark.

## CI considerations

- Run backend unit/integration tests (with mocked Ollama) and frontend component tests on every PR.
- E2E tests and any test requiring a real Ollama instance run less frequently (e.g., nightly or pre-release) given their cost/flakiness, not on every commit.
- Never run AI quality spot-checks as a CI gate — they're a human process, not a pass/fail automated check, per the philosophy above.
