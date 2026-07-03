# 03 — Database Schema

This document defines every table the platform needs, grouped by module, with columns, types, relationships, and notes. It is written so an AI agent can generate SQLAlchemy models and Alembic migrations directly from it.

## Conventions

- Primary keys: `id INTEGER PRIMARY KEY AUTOINCREMENT` (SQLite). When migrating to Postgres later, switch to `BIGSERIAL`/UUID per `Future Postgres Migration` section below.
- All tables have `created_at` and `updated_at` (`DATETIME`, default `CURRENT_TIMESTAMP`, `updated_at` auto-updated on write).
- Soft delete via `is_deleted BOOLEAN DEFAULT FALSE` on tables where hard-deleting would break referential history (students, questions, papers, results). Hard delete is acceptable for purely operational tables (sessions, cache).
- Every school-scoped table has `school_id INTEGER NOT NULL REFERENCES schools(id)`.
- Multi-language text columns use suffixes: `_en`, `_hi`, `_gu`. At least `_en` is required (NOT NULL); `_hi`/`_gu` are nullable until translated.
- Foreign keys are named `<referenced_table_singular>_id`.

---

## 1. Authentication & Identity

### `schools`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| name | TEXT NOT NULL | |
| udise_code | TEXT UNIQUE | Government school identifier |
| district_id | INTEGER REFERENCES districts(id) | |
| address | TEXT | |
| board | TEXT DEFAULT 'GSEB' | |
| medium | TEXT | e.g. Gujarati, English, Hindi |
| is_active | BOOLEAN DEFAULT TRUE | |

### `districts`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| name | TEXT NOT NULL | |
| state | TEXT DEFAULT 'Gujarat' | |

### `users`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| school_id | INTEGER REFERENCES schools(id) | Nullable for DEO-level users who span schools |
| district_id | INTEGER REFERENCES districts(id) | Populated for DEO role |
| full_name | TEXT NOT NULL | |
| email | TEXT UNIQUE NOT NULL | Used as login |
| phone | TEXT | |
| password_hash | TEXT NOT NULL | bcrypt/argon2, see `12-security.md` |
| role | TEXT NOT NULL | `administrator`, `teacher`, `principal`, `deo` |
| preferred_language | TEXT DEFAULT 'en' | `en`/`hi`/`gu` |
| is_active | BOOLEAN DEFAULT TRUE | |
| last_login_at | DATETIME | |

### `refresh_tokens`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| user_id | INTEGER REFERENCES users(id) | |
| token_hash | TEXT NOT NULL | Never store raw token |
| expires_at | DATETIME NOT NULL | |
| revoked | BOOLEAN DEFAULT FALSE | |

---

## 2. Schools, Teachers, Students, Classes, Subjects

### `teachers`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| user_id | INTEGER UNIQUE REFERENCES users(id) | 1:1 with users where role=teacher |
| school_id | INTEGER REFERENCES schools(id) | |
| employee_code | TEXT | |
| subjects_taught | TEXT | comma-separated `subject_id`s, or normalize via join table `teacher_subjects` if multi-valued queries are needed |

### `classes`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| school_id | INTEGER REFERENCES schools(id) | |
| grade | INTEGER NOT NULL | e.g. 8, 9, 10 |
| section | TEXT | e.g. "A" |
| academic_year | TEXT NOT NULL | e.g. "2026-27" |
| class_teacher_id | INTEGER REFERENCES teachers(id) | |

### `students`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| school_id | INTEGER REFERENCES schools(id) | |
| class_id | INTEGER REFERENCES classes(id) | |
| full_name | TEXT NOT NULL | |
| roll_number | TEXT NOT NULL | Unique within class |
| gr_number | TEXT | Government register number |
| gender | TEXT | |
| date_of_birth | DATE | |
| is_active | BOOLEAN DEFAULT TRUE | |

### `subjects`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| name_en | TEXT NOT NULL | |
| name_hi | TEXT | |
| name_gu | TEXT | |
| code | TEXT UNIQUE | e.g. `MATH8` |
| grade | INTEGER | Subjects are grade-specific in GSEB |

---

## 3. Curriculum Knowledge Graph

### `books`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| school_id | INTEGER REFERENCES schools(id) | |
| subject_id | INTEGER REFERENCES subjects(id) | |
| grade | INTEGER NOT NULL | |
| title | TEXT NOT NULL | |
| file_path | TEXT NOT NULL | Path in Shared File Storage |
| source_type | TEXT | `textbook`, `teacher_notes`, `worksheet`, `pdf` |
| processing_status | TEXT DEFAULT 'uploaded' | `uploaded`, `extracting_text`, `building_curriculum`, `extracting_concepts`, `mapping_competencies`, `ready`, `failed_at_<stage>` |
| processing_error | TEXT | Last error message if failed |
| uploaded_by | INTEGER REFERENCES users(id) | |

### `chapters`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| book_id | INTEGER REFERENCES books(id) | |
| unit_name | TEXT | Some GSEB books group chapters into units |
| sequence | INTEGER | Order within book |
| title_en / title_hi / title_gu | TEXT | |

### `topics`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| chapter_id | INTEGER REFERENCES chapters(id) | |
| sequence | INTEGER | |
| title_en / title_hi / title_gu | TEXT | |

### `concepts`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| topic_id | INTEGER REFERENCES topics(id) | |
| name_en / name_hi / name_gu | TEXT | |
| description | TEXT | |
| extracted_by | TEXT DEFAULT 'ai' | `ai` or `manual`, for audit/trust purposes |

### `learning_outcomes`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| concept_id | INTEGER REFERENCES concepts(id) | |
| code | TEXT | GSEB/NCERT LO code if applicable |
| description_en / description_hi / description_gu | TEXT | |

### `competencies`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| name_en / name_hi / name_gu | TEXT | |
| nas_parakh_code | TEXT | Official PARAKH competency code, if mapped |
| description | TEXT | |

### `learning_outcome_competencies` (join table)
| Column | Type | Notes |
|---|---|---|
| learning_outcome_id | INTEGER REFERENCES learning_outcomes(id) | |
| competency_id | INTEGER REFERENCES competencies(id) | |

### `knowledge_chunks`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| book_id | INTEGER REFERENCES books(id) | |
| chapter_id | INTEGER REFERENCES chapters(id) | nullable |
| chunk_text | TEXT NOT NULL | |
| chunk_index | INTEGER | Order within book |
| chroma_vector_id | TEXT UNIQUE | ID of the corresponding vector in ChromaDB — **the actual embedding lives in ChromaDB, not SQLite; this column is the join key** |
| token_count | INTEGER | |

### `ai_analysis`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| book_id | INTEGER REFERENCES books(id) | |
| stage | TEXT NOT NULL | `concept_extraction`, `competency_mapping`, etc. |
| input_ref | TEXT | What was analyzed (e.g. chunk id) |
| raw_llm_output | TEXT | Stored for debugging/auditing AI output |
| status | TEXT | `success`, `failed`, `needs_review` |

---

## 4. Question Bank

### `question_bank`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| school_id | INTEGER REFERENCES schools(id) | |
| concept_id | INTEGER REFERENCES concepts(id) | |
| competency_id | INTEGER REFERENCES competencies(id) | |
| learning_outcome_id | INTEGER REFERENCES learning_outcomes(id) | |
| question_text_en / _hi / _gu | TEXT | |
| question_type | TEXT NOT NULL | `mcq`, `short_answer`, `long_answer`, `true_false`, `fill_blank` |
| bloom_level | TEXT NOT NULL | `remember`, `understand`, `apply`, `analyze`, `evaluate`, `create` |
| difficulty | TEXT NOT NULL | `easy`, `medium`, `hard` |
| marks | DECIMAL(4,1) NOT NULL | |
| estimated_time_seconds | INTEGER | |
| explanation_en / _hi / _gu | TEXT | Shown after scoring / for teacher review |
| confidence_score | FLOAT | 0–1, from AI Quality Control (see `08-question-engine.md`) |
| duplicate_score | FLOAT | 0–1, similarity to nearest existing question |
| generated_by | TEXT DEFAULT 'ai' | `ai` or `manual` |
| approval_status | TEXT DEFAULT 'pending_review' | `pending_review`, `approved`, `rejected`, `needs_edit` |
| approved_by | INTEGER REFERENCES users(id) | |
| approved_at | DATETIME | |
| is_deleted | BOOLEAN DEFAULT FALSE | |

### `question_options`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| question_id | INTEGER REFERENCES question_bank(id) | |
| option_text_en / _hi / _gu | TEXT | |
| is_correct | BOOLEAN DEFAULT FALSE | |
| sequence | INTEGER | Display order (pre-shuffle) |

---

## 5. Blueprints & Papers

### `blueprints`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| school_id | INTEGER REFERENCES schools(id) | |
| created_by | INTEGER REFERENCES users(id) | |
| name | TEXT NOT NULL | |
| grade | INTEGER NOT NULL | |
| subject_id | INTEGER REFERENCES subjects(id) | |
| chapter_ids | TEXT | JSON array of chapter ids in scope |
| total_questions | INTEGER NOT NULL | |
| total_marks | DECIMAL(6,1) NOT NULL | |
| difficulty_distribution | TEXT | JSON, e.g. `{"easy":40,"medium":40,"hard":20}` (percentages) |
| bloom_distribution | TEXT | JSON, percentages per Bloom level |
| competency_distribution | TEXT | JSON, percentages or explicit counts per competency_id |
| duration_minutes | INTEGER | |

### `papers`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| blueprint_id | INTEGER REFERENCES blueprints(id) | |
| variant_label | TEXT NOT NULL | `A`, `B`, `C`, ... |
| pdf_file_path | TEXT | Rendered paper PDF location |
| generated_at | DATETIME | |
| generated_by | INTEGER REFERENCES users(id) | |

### `paper_questions`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| paper_id | INTEGER REFERENCES papers(id) | |
| question_id | INTEGER REFERENCES question_bank(id) | |
| sequence | INTEGER NOT NULL | Position in this paper variant |
| option_order | TEXT | JSON array recording the shuffled option order used for this variant, so OMR scoring can map bubble position back to the correct option |

---

## 6. OMR

### `omr_sheets`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| paper_id | INTEGER REFERENCES papers(id) | |
| student_id | INTEGER REFERENCES students(id) | nullable until assigned/printed per student |
| assessment_id | INTEGER REFERENCES assessments(id) | |
| qr_payload | TEXT | Encoded student_id+assessment_id+paper_id+checksum |
| barcode_payload | TEXT | |
| sheet_pdf_path | TEXT | |
| status | TEXT DEFAULT 'generated' | `generated`, `printed`, `scanned`, `scan_failed` |

### `omr_results`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| omr_sheet_id | INTEGER REFERENCES omr_sheets(id) | |
| scanned_image_path | TEXT | Original uploaded scan |
| detected_answers | TEXT | JSON array, bubble index per question |
| raw_score | DECIMAL(6,1) | |
| max_score | DECIMAL(6,1) | |
| scan_confidence | FLOAT | OpenCV detection confidence, flags low-confidence scans for manual review |
| needs_manual_review | BOOLEAN DEFAULT FALSE | |
| scanned_by | INTEGER REFERENCES users(id) | |
| scanned_at | DATETIME | |

---

## 7. Assessments & Results

### `assessments`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| school_id | INTEGER REFERENCES schools(id) | |
| blueprint_id | INTEGER REFERENCES blueprints(id) | |
| class_id | INTEGER REFERENCES classes(id) | |
| name | TEXT NOT NULL | |
| scheduled_date | DATE | |
| status | TEXT DEFAULT 'scheduled' | `scheduled`, `conducted`, `scored`, `published` |

### `student_results`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| assessment_id | INTEGER REFERENCES assessments(id) | |
| student_id | INTEGER REFERENCES students(id) | |
| omr_result_id | INTEGER REFERENCES omr_results(id) | nullable if manually entered |
| total_score | DECIMAL(6,1) | |
| max_score | DECIMAL(6,1) | |
| percentage | FLOAT | |

### `competency_results`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| student_result_id | INTEGER REFERENCES student_results(id) | |
| competency_id | INTEGER REFERENCES competencies(id) | |
| questions_attempted | INTEGER | |
| questions_correct | INTEGER | |
| mastery_level | TEXT | `weak`, `developing`, `proficient`, `advanced` — derived, see `11-analytics-engine.md` |

---

## 8. Reports, Analytics, Audit, Backup, Settings

### `reports`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| school_id | INTEGER REFERENCES schools(id) | |
| report_type | TEXT | `student`, `class`, `school`, `district` |
| reference_id | INTEGER | id of the student/class/school/district this report is about |
| file_path | TEXT | Generated PDF |
| generated_at | DATETIME | |
| generated_by | INTEGER REFERENCES users(id) | |

### `analytics_cache`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| cache_key | TEXT UNIQUE NOT NULL | e.g. `class:42:competency_trends:2026-27` |
| payload | TEXT | JSON |
| computed_at | DATETIME | |
| expires_at | DATETIME | |

### `audit_logs`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| user_id | INTEGER REFERENCES users(id) | |
| school_id | INTEGER REFERENCES schools(id) | |
| action | TEXT NOT NULL | e.g. `question.approve`, `student.create`, `paper.generate` |
| resource_type | TEXT | |
| resource_id | INTEGER | |
| metadata | TEXT | JSON, request details (no sensitive payloads) |
| ip_address | TEXT | |
| created_at | DATETIME | |

See `12-security.md` for the full list of actions that must be audited.

### `backups`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| school_id | INTEGER REFERENCES schools(id) | |
| file_path | TEXT | |
| backup_type | TEXT | `full`, `db_only` |
| size_bytes | INTEGER | |
| created_at | DATETIME | |
| created_by | INTEGER REFERENCES users(id) | |

### `settings`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| school_id | INTEGER REFERENCES schools(id) | nullable for global/system settings |
| key | TEXT NOT NULL | |
| value | TEXT | JSON or plain string |
| UNIQUE(school_id, key) | | |

---

## Entity relationship summary (text form)

```
schools 1—N users
schools 1—N classes 1—N students
schools 1—N books 1—N chapters 1—N topics 1—N concepts 1—N learning_outcomes N—N competencies
books 1—N knowledge_chunks (→ ChromaDB vectors via chroma_vector_id)
concepts/competencies/learning_outcomes 1—N question_bank 1—N question_options
blueprints 1—N papers 1—N paper_questions → question_bank
papers 1—N omr_sheets 1—1 omr_results
assessments 1—N student_results 1—N competency_results
all major mutating actions → audit_logs
```

## Indexing notes

- Index every foreign key column.
- Composite index on `question_bank(school_id, approval_status, concept_id)` — this is the hot path for paper generation queries.
- Composite index on `students(class_id, roll_number)`.
- Index `audit_logs(school_id, created_at)` for log review/pagination.
- `knowledge_chunks(book_id, chunk_index)` for ordered re-assembly.

## Future Postgres Migration

Design choices to make this painless later:

- Use SQLAlchemy's database-agnostic types (`String`, `Integer`, `Boolean`, `DateTime`, `JSON`) rather than SQLite-specific types. SQLAlchemy's `JSON` type works on both SQLite (as TEXT) and Postgres (as native JSONB) — use it instead of manually serializing JSON into TEXT columns where the ORM supports it directly.
- Avoid SQLite-only features (no `ROWID` aliasing tricks, no `PRAGMA`-dependent behavior in application code).
- Keep all schema changes in Alembic migrations from day one, even before there's a second environment — this is what makes a future `alembic upgrade head` against Postgres trustworthy.
- When migrating, primary keys can move from `INTEGER AUTOINCREMENT` to `BIGSERIAL`/UUID without changing any application code that uses SQLAlchemy relationships (not raw IDs) to navigate.
- `analytics_cache` and `refresh_tokens` are good candidates to move to Redis in a future scale-up, but ship as SQL tables for v1 to avoid adding Redis as a v1 dependency.
