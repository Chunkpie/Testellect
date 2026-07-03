# 08 — Question Engine

## Scope

Covers question generation (via the AI Pipeline's Question Generation Agent), the AI Quality Control scoring system, the human review/approval workflow, and the Blueprint-based Paper Generator's question selection algorithm.

## Question metadata (recap from schema)

Every question in `question_bank` carries: concept, competency, learning outcome, Bloom level, difficulty, marks, estimated time, explanation, confidence score, duplicate score, approval status. See `03-database-schema.md` for exact columns.

## Question Generation flow

1. A generation request specifies a target: `concept_id` (required), optionally `competency_id`, `bloom_level`, `difficulty`, `question_type`, and `count` (how many candidates to generate).
2. Requests originate from two places:
   - **Direct teacher request**: "generate 5 more questions for this concept" from the Question Bank UI.
   - **Coverage-gap-driven**: when a Blueprint's required distribution can't be satisfied by existing approved questions (see "Selection Algorithm" below), the Paper Generator can optionally trigger generation requests to fill the gap, surfaced to the teacher as "We need N more questions of type X — generate now?" rather than silently blocking paper generation.
3. The Question Generation Agent retrieves grounding context (per `07-rag-architecture.md`) scoped to the target concept, assembles the prompt (per `20-ai-prompt-library.md` → "Question Generation Prompt"), and calls Ollama with `format: "json"`.
4. The LLM response is parsed into one or more candidate questions (question text in the requesting language(s), options if MCQ, suggested explanation) and written to `question_bank` with `approval_status = 'pending_review'` and `generated_by = 'ai'`.
5. Each candidate immediately proceeds to the Question Validation Agent (AI Quality Control) before the teacher even sees it, so the review queue is pre-scored.

## AI Quality Control — scoring dimensions

Each generated question is scored on:

| Dimension | How it's computed |
|---|---|
| Concept Accuracy | LLM self-critique pass: given the question + the source chunk(s), ask the model "does this question accurately test the stated concept, yes/no + brief reason" (see `20-ai-prompt-library.md` → "Validation Prompt") |
| Bloom Classification | LLM classifies the generated question's actual cognitive demand independently, compared against the requested `bloom_level` — mismatch lowers confidence |
| Difficulty | Heuristic + LLM estimate (e.g., question length, number of reasoning steps implied, vocabulary complexity) compared against requested `difficulty` |
| Competency Coverage | Checks the question text actually exercises the mapped competency (LLM judgment) rather than only superficially mentioning the concept |
| Duplicate Risk | Vector similarity (via ChromaDB or a direct embedding comparison) between the new question's text and existing `question_bank` entries for the same concept; high similarity → high `duplicate_score` |
| Language Quality | Grammar/clarity check, especially important for non-English (Hindi/Gujarati) generations where local model output may be weaker — flag for closer teacher review rather than silently accepting |

Combine into a single `confidence_score` (0–1) using a simple weighted average (exact weights are an implementation tuning decision, not fixed by this spec) — the score's job is to **prioritize the teacher's review queue** (sort lowest-confidence first, or highest-confidence first depending on UX preference — recommend surfacing both "needs closer look" and "likely fine" groupings rather than a single opaque number) and to **never replace human review.**

## Human review workflow

- Review queue UI (per `05-frontend-specification.md`) shows `pending_review` questions filterable by concept/competency/Bloom/confidence.
- Teacher actions: **Approve** (sets `approval_status='approved'`, `approved_by`, `approved_at`), **Reject** (sets `approval_status='rejected'`, soft-kept for audit, excluded from all future selection), **Edit then Approve** (teacher modifies question text/options/tags inline, then approves — the edit itself should be audit-logged as `question.edit`).
- Only `approval_status='approved'` questions are ever eligible for paper selection (see below). This is enforced at the query level in `paper_generator.py`, not just at the UI level — a malformed request should not be able to select unapproved questions.

## Manual question authoring

Teachers can also author questions directly (Rich Question Editor, `generated_by='manual'`). Manual questions can optionally still go through AI Quality Control scoring (useful feedback even for human-written questions) but typically skip the `pending_review` gate and go straight to `approved` if the teacher submits them as final — implement this as an explicit "Save as Draft" vs "Save and Approve" choice in the editor UI, defaulting to draft to avoid accidental publishing of half-finished questions.

## Selection Algorithm (Blueprint → Paper)

Given a `blueprint_id` with `total_questions`, `difficulty_distribution`, `bloom_distribution`, `competency_distribution`, and `chapter_ids` scope:

1. Query `question_bank` for `approval_status='approved'`, `school_id` matches, concept's chapter in `chapter_ids`.
2. Compute the target count per distribution bucket (e.g., if `total_questions=20` and `difficulty_distribution={"easy":40,"medium":40,"hard":20}`, target is 8 easy / 8 medium / 4 hard).
3. For each bucket combination (difficulty × Bloom level × competency, where specified), attempt to randomly select the required count from matching approved questions.
4. If any bucket is under-filled (not enough approved questions matching that combination), report the **specific shortfall** back to the caller (e.g., "Need 3 more 'hard' + 'analyze' + 'fractions' questions, only 1 available") rather than silently relaxing the blueprint or generating a paper that doesn't match what the teacher asked for.
5. Only once all buckets are satisfiable does paper generation proceed to actually building variants.
6. For multiple variants (Paper A/B/C), reuse the same selected question *set* but shuffle question order and, for MCQ, shuffle option order independently per variant — record the resulting per-variant option order in `paper_questions.option_order` (per `03-database-schema.md`) so OMR scoring later maps the correct bubble position back to the right answer for that specific variant.

```python
# services/question_engine.py (conceptual selection core)
def select_questions_for_blueprint(db, blueprint: Blueprint) -> SelectionResult:
    buckets = compute_target_buckets(blueprint)
    selected = []
    shortfalls = []
    for bucket in buckets:
        candidates = query_approved_questions(db, blueprint.school_id, bucket)
        if len(candidates) < bucket.target_count:
            shortfalls.append(Shortfall(bucket=bucket, available=len(candidates), needed=bucket.target_count))
            continue
        selected += random.sample(candidates, bucket.target_count)
    if shortfalls:
        return SelectionResult(success=False, shortfalls=shortfalls)
    return SelectionResult(success=True, questions=selected)
```

## Preventing duplicate questions across papers

Because the selection algorithm samples from the same approved pool, the same question can legitimately appear across multiple unrelated papers over time (that's fine and expected — it's a reusable bank). What must be prevented is duplicate/near-duplicate questions *within* the bank itself going unnoticed — that's what `duplicate_score` at generation time is for. Consider a periodic (not per-request) background job that re-scans the approved bank for near-duplicates as the bank grows, surfacing a "possible duplicates" admin view rather than trying to catch everything synchronously at generation time.

## Question types and rendering implications

| Type | OMR-compatible? | Notes |
|---|---|---|
| `mcq` | Yes | Standard bubble format |
| `true_false` | Yes | 2-option bubble format |
| `fill_blank` | Limited | OMR can't capture free text; either restrict to a small bubble-selectable answer bank per blank, or route to manual scoring |
| `short_answer` / `long_answer` | No | Always manually scored by the teacher; the platform should support recording a manually-entered score for these per student even when the rest of the paper is OMR-scored — see `09-omr-engine.md` → "Mixed Question Type Papers" |

Surface this distinction in the Blueprint Builder UI: if a teacher includes `short_answer`/`long_answer` questions in a blueprint intended for OMR scanning, warn them that those specific questions will need manual marks entry.
