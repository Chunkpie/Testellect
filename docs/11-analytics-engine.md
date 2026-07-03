# 11 — Analytics Engine

## Scope

Defines how raw `student_results`/`competency_results` data is aggregated into the dashboards described in the project summary (Teacher, Principal, DEO) and how mastery levels are derived.

## Mastery level derivation

`competency_results.mastery_level` is computed per `(student, competency)` pair from `questions_attempted`/`questions_correct`, using simple, explainable thresholds rather than an opaque model — analytics that a teacher can't sanity-check are not useful for an educational tool:

| Accuracy on this competency | Mastery level |
|---|---|
| < 40% | `weak` |
| 40–64% | `developing` |
| 65–84% | `proficient` |
| ≥ 85% | `advanced` |

Require a minimum sample size (e.g., at least 3 questions attempted for that competency) before assigning anything other than `developing` as a default/provisional label — a single wrong answer on a competency with only one question seen so far shouldn't brand a student "weak" on it. Surface the attempted-count alongside the label in the UI so low-confidence labels are visually distinguishable (e.g., a small "based on 2 questions" caption).

## Teacher Dashboard

- **Student Progress**: per-student trend line of scores across assessments over the current academic year/term.
- **Weak Concepts**: aggregated across the teacher's class(es), which concepts have the lowest average accuracy — this drives re-teaching priorities. Implemented as a query grouping `competency_results` (joined back to `concepts` via `learning_outcome_competencies`) by concept, filtered to the teacher's classes, sorted ascending by average accuracy.
- **Competency Performance**: per-class heatmap, students (rows) × competencies (columns), cell color = mastery level.

## Principal Dashboard

- **Class Comparison**: average score and competency mastery distribution across all classes in the school, same grade level compared together (comparing Grade 6 to Grade 10 directly is misleading — always group comparisons by grade).
- **Teacher Performance**: framed as *class outcomes associated with each teacher's sections*, not a direct judgment of teaching quality in isolation — be careful in UI copy here; this view should explicitly avoid implying causation it can't support (a teacher with a historically weaker-incoming class will show different aggregate numbers than one with a stronger-incoming class, and the dashboard has no way to control for that). Frame as "class outcomes" with a visible caveat, not a teacher leaderboard.
- **School Reports**: rollup feeding `10-report-engine.md`'s School Report.

## DEO Dashboard

- **School Comparison**: same caveats as Teacher Performance above, applied at school level — control for grade level in every comparison, and avoid ranking presentations that incentivize gaming the assessment rather than improving learning.
- **District Analytics**: aggregate competency mastery distribution across all schools in the district.
- **Competency Trends**: time-series view (per term/year) showing whether district-wide mastery of specific competencies is improving, useful for curriculum/training interventions at the district level.

## Caching strategy

- Every dashboard query that aggregates across more than a single student (class-level and above) is a candidate for `analytics_cache` (per `03-database-schema.md`).
- Cache key pattern: `{scope_type}:{scope_id}:{metric}:{academic_year}` e.g. `class:42:competency_trends:2026-27`.
- Invalidate (or let expire via TTL, e.g. 1 hour) whenever new `student_results`/`competency_results` are written for that scope — simplest correct approach for v1 is TTL-based expiry rather than precise invalidation, given the relatively low write frequency (results land in batches after assessments, not continuously).

## Computing competency_results from OMR/manual scoring

After an `omr_result` (or manual entry) produces per-question correctness for a student, a post-processing step writes one `competency_results` row per distinct competency touched by that assessment's questions, aggregating `questions_attempted`/`questions_correct` across all questions in that assessment mapped to that competency (a single assessment's paper typically touches several competencies across its 15–30 questions, not one-to-one). This step lives in `services/analytics_engine.py` (`compute_competency_results(assessment_id, student_id)`), triggered right after scoring completes (OMR scan finishes, or manual marks entry is submitted) — not deferred to dashboard load time, so dashboards stay fast reads over pre-aggregated data.

## What this module deliberately does not do

- No predictive modeling (e.g., "predicted NAS score") in v1 — the data volume per school is too small for that to be trustworthy, and an unreliable prediction is worse than no prediction in an educational context. If this is wanted later, it belongs in `19-roadmap.md` as an explicit future phase with its own validation requirements, not bolted on here.
- No cross-school ranking leaderboards visible to schools/teachers themselves (DEO-level comparison views are internal to district administration, not surfaced competitively to schools) — this is a deliberate design choice to avoid incentivizing score-gaming over genuine learning improvement.
