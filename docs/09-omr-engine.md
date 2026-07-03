# 09 — OMR Engine

## Scope

Covers OMR sheet generation (PDF layout with QR/barcode identifiers) and the OpenCV-based scanning pipeline that turns a photographed/scanned completed sheet into scored results.

## OMR Sheet Generation

### Identifiers
Each generated sheet (`omr_sheets` table) encodes:
- A **QR code** containing a JSON-ish payload: `{paper_id, student_id, assessment_id, checksum}` — the checksum (e.g., a short CRC or HMAC truncation using a server-side secret) protects against tampering/misread.
- A **barcode** (e.g., Code128) encoding a simpler numeric ID for fallback scanning on lower-quality cameras where QR decode might fail.
- Both are generated server-side (Python: `qrcode` library for QR, `python-barcode` for Code128) and embedded into the ReportLab-rendered PDF alongside the bubble grid.

### Layout requirements
- Fixed-position bubble grid with generous spacing (OpenCV detection accuracy depends heavily on consistent, well-separated bubble positions) — define the grid layout as a configuration (rows/cols, bubble diameter, spacing) reused identically across every generated sheet so the scanning pipeline can rely on known geometry rather than re-detecting layout from scratch each time.
- Corner registration markers (solid black squares at 3 or 4 corners) so OpenCV's perspective correction step has reliable anchor points regardless of how the sheet was photographed (slight rotation, skew, partial shadow).
- Student name/roll number printed in human-readable text near the QR/barcode (so a misread code can be manually corrected by a human glancing at the sheet).
- Each question's bubble row is labeled with the question number; for MCQ, label option positions A/B/C/D (or however many options) per `paper_questions.option_order` for that specific paper variant.

### Per-student vs. generic sheets
- If `student_id` is known at generation time (sheet pre-assigned to a specific student before printing), encode it directly — this is the preferred flow for in-school exams.
- If sheets are printed generically (no pre-assigned student, e.g., for walk-in or flexible seating), leave `student_id` null and require the student to bubble-fill their roll number in a dedicated grid on the sheet itself; the scanning pipeline must then read that bubble-filled roll number grid to identify the student instead of relying on the QR payload alone.

## Scanning Pipeline (OpenCV)

```
Uploaded image
   │
   ▼
1. Preprocessing       — grayscale, denoise, adaptive threshold
   │
   ▼
2. Corner detection      — locate the 3-4 registration markers
   │
   ▼
3. Perspective correction — warp transform to a canonical flat rectangle using detected corners
   │
   ▼
4. QR/barcode decode      — pyzbar (or OpenCV's built-in QRCodeDetector) to extract student/paper/assessment IDs
   │
   ▼
5. Bubble grid detection  — using the known fixed layout config, sample expected bubble regions
   │
   ▼
6. Bubble fill detection  — for each expected bubble region, compute filled-pixel ratio; mark "filled" above a threshold
   │
   ▼
7. Multi-mark / blank detection — flag questions with 0 or >1 filled bubbles as ambiguous
   │
   ▼
8. Answer mapping          — map filled bubble position → option, using paper_questions.option_order for that variant (NOT a fixed A/B/C/D assumption, since option order is shuffled per variant)
   │
   ▼
9. Scoring                  — compare mapped answers to question_options.is_correct, compute raw_score
   │
   ▼
10. Confidence + review flag — overall scan_confidence from corner-detection quality + ambiguous-bubble count; needs_manual_review=true if below threshold or any ambiguous bubbles exist
```

### Implementation notes per stage

- **Step 2–3 (registration/perspective)**: use `cv2.findContours` + shape filtering to locate the corner squares, then `cv2.getPerspectiveTransform` + `cv2.warpPerspective`. If fewer than 3 corners are confidently detected, fail this scan immediately with a clear "could not register sheet, please rescan" error rather than guessing at geometry.
- **Step 6 (fill detection)**: don't use a single global threshold for "filled" — normalize against the local background (some scans are darker/lighter overall due to lighting/camera) by comparing each bubble's fill ratio against the page's empty-bubble baseline.
- **Step 7**: an unmarked question should be recorded distinctly from an "ambiguous/multi-marked" question in `omr_results.detected_answers` (e.g., `null` vs a sentinel like `"AMBIGUOUS"`) so downstream scoring and the manual-review UI can treat them differently — a blank answer is simply wrong; an ambiguous one needs a human's eyes.

### Batch scanning
Support uploading multiple sheet images in one request (`POST /api/v1/omr/scan/batch`), processing each independently (one failure shouldn't abort the batch), returning a per-sheet result list with status (`scored`, `needs_manual_review`, `scan_failed` + reason).

### Manual review/correction UI
For `needs_manual_review` results, show the original uploaded image alongside the system's best-guess answers, letting a teacher click to confirm/correct individual ambiguous questions rather than re-scanning the physical sheet. Corrections update `omr_results.detected_answers` and are audit-logged (`omr_result.manual_correct`).

## Mixed Question Type Papers

When a paper contains `short_answer`/`long_answer` questions alongside OMR-scannable ones (per `08-question-engine.md`):
- The OMR scan only scores the bubble-able questions.
- The remaining marks (for non-bubble questions) are entered manually per student via a simple marks-entry UI, associated with the same `student_results` row, summed into `total_score` alongside the OMR-derived score.
- `student_results.max_score` accounts for the full paper (OMR-portion + manually-scored portion), not just the OMR portion, so percentages are correct.

## Calibration and testing

Before relying on this pipeline for real assessments, test against a deliberately varied set of sample scans: slightly rotated, photographed at an angle, under uneven lighting, with stray pencil marks, with an eraser smudge over a bubble. See `15-testing.md` → "OMR Engine Test Cases" for the specific scenarios that must be covered before this module is considered done.
