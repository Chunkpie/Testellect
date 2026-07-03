# 10 — Report Engine

## Scope

Covers generation of PDF reports (student, class, school, district level) using ReportLab, consuming data produced by `11-analytics-engine.md`.

## Report types

| Type | Audience | Contents |
|---|---|---|
| Student Report | Parent/teacher | Individual student's results across assessments, competency-level breakdown (mastery per competency), trend over time, weak concepts list |
| Class Report | Teacher/Principal | Class-wide score distribution, competency performance heatmap across students, comparison to school average |
| School Report | Principal/DEO | Class-by-class comparison, teacher performance summary (in aggregate, not punitive framing), school-wide competency trends |
| District Report | DEO | School-by-school comparison, district-wide competency trends, identification of systemic weak areas |

## Architecture

- `services/report_engine.py` is the single place that knows how to render any report type to PDF. It takes a `report_type` + `reference_id` + date range, pulls pre-computed data from `services/analytics_engine.py` (never recomputes analytics itself — strict separation of concerns from `11-analytics-engine.md`), and renders via ReportLab templates.
- One ReportLab template function per report type (`render_student_report(data) -> bytes`, etc.), each composed from shared building blocks (a header/letterhead component, a score-table component, a chart-embedding component) rather than four entirely separate, copy-pasted layouts.
- Generated PDFs are saved to Shared File Storage and recorded in the `reports` table (per `03-database-schema.md`), with a `GET /api/v1/reports/{id}/download` endpoint serving the file (auth-checked: a teacher can only download reports for their own school; a DEO can download for their district).

## Embedding charts in PDF reports

ReportLab doesn't have built-in rich charting comparable to a JS charting library, but it does include `reportlab.graphics.charts` (bar charts, line charts, pie charts) which is sufficient for score distributions and trend lines. For more complex visuals (e.g., a competency heatmap grid), render the chart as an image (e.g., via `matplotlib` with the `Agg` backend, no display server needed — fits the headless server environment) and embed the resulting PNG into the ReportLab flowable, rather than trying to force ReportLab's native chart primitives to do something they're not well-suited for.

## Letterhead / branding

- Each school can configure a logo (stored via Settings, `settings` table key like `school_logo_path`) and have it appear on report headers; fall back to a generic GSEB-branded header if no school logo is configured.
- Reports should always show: school name, report generation date, the date range/assessment(s) covered, and who generated it (for audit trust) — this last detail comes from `reports.generated_by`.

## Language of generated reports

Reports default to the requesting user's `preferred_language`, with question/competency names pulled from the matching `_en`/`_hi`/`_gu` column (consistent with `05-frontend-specification.md`'s i18n approach for domain content) — but note that score tables, charts, and numeric data are language-agnostic, so only labels/headers/competency names need localization, not the underlying data tables.

## Report generation triggers

- **On-demand**: teacher/principal/DEO clicks "Generate Report" in the Reports module UI for a chosen scope and date range.
- **Post-assessment**: optionally, generating a class report automatically once an assessment moves to `status='scored'` (configurable per-school setting, default off for v1 to avoid surprising teachers with auto-generated PDFs they didn't ask for).

## Performance note

PDF rendering with embedded matplotlib charts for, say, a district report spanning many schools, can be slow on modest hardware. Generate these as background jobs (same job-table pattern as `04-backend-specification.md` → "Background Jobs"), not synchronously within the HTTP request, and let the UI poll for completion the same way book processing status is polled.
