# 07 — RAG Architecture

## Purpose

Defines how content gets embedded, stored, and retrieved from ChromaDB to ground every LLM call in `06-ai-engine.md` against actual curriculum content, rather than the model's unguided memory.

## Why RAG here specifically

Qwen3 8B, like any local 8B-class model, doesn't reliably "know" the contents of a specific GSEB Grade 8 Science textbook. RAG is what lets the platform generate accurate, source-grounded questions and explanations instead of plausible-sounding-but-wrong content (a particularly serious failure mode for an educational tool). Every generative call in the pipeline should include retrieved chunks as context.

## Embedding model

Use a local embedding model runnable via Ollama (e.g., `nomic-embed-text` or a similarly sized multilingual-capable embedding model available in the Ollama model library) rather than calling a hosted embeddings API — this keeps the embedding step offline like everything else. Confirm at implementation time which embedding model is available and pull it alongside Qwen3 8B in the same Ollama instance (see `14-docker-deployment.md` → "Model Provisioning").

For Gujarati/Hindi content, verify the chosen embedding model has reasonable multilingual support; if not, consider embedding each chunk in its original language only (don't force-translate before embedding) and accept that cross-language semantic search is a stretch goal, not a v1 guarantee.

## Chunking strategy

- Chunk size target: 300–500 tokens, with ~50-token overlap between consecutive chunks to avoid splitting a concept explanation mid-thought.
- Chunk at sentence/paragraph boundaries, never mid-sentence — use a simple recursive splitter (split on paragraph breaks first, fall back to sentence breaks if a paragraph is too long) rather than a fixed character-count cut.
- Each chunk retains a back-reference to its `book_id` and (once known) `chapter_id`, stored both in SQLite (`knowledge_chunks` table, per `03-database-schema.md`) and as Chroma metadata, so retrieved chunks can always be traced back to their source.

## ChromaDB collection design

- One Chroma collection per school (e.g., `school_{school_id}_curriculum`), not one global collection — this keeps retrieval scoped naturally and avoids cross-school content ever leaking into another school's generation calls, which matters once multi-school/district deployments exist.
- Metadata stored per vector: `book_id`, `chapter_id`, `topic_id` (once assigned), `grade`, `subject_id`, `language`.
- The `knowledge_chunks.chroma_vector_id` column (per `03-database-schema.md`) is the join key between SQLite and Chroma — always write the SQLite row and the Chroma vector together (in the same logical operation, with rollback-on-failure handling) so they never drift out of sync. If the Chroma write fails, the SQLite row should not be committed (or should be marked and retried), and vice versa.

## Retrieval pattern used by every agent

```python
# services/ai_pipeline/retrieval.py (conceptual)
async def retrieve_context(school_id: int, query_text: str, filters: dict, top_k: int = 5) -> list[Chunk]:
    collection = chroma_client.get_collection(f"school_{school_id}_curriculum")
    results = collection.query(
        query_texts=[query_text],
        n_results=top_k,
        where=filters,  # e.g. {"topic_id": 42} to scope retrieval tightly
    )
    return parse_chunks(results)
```

- **Always scope retrieval as tightly as the task allows.** Concept extraction for a specific topic should query with `where={"topic_id": topic_id}`, not search the whole school's corpus — broad retrieval increases the chance of irrelevant or cross-chapter contamination in generated content.
- For the AI Teacher Assistant (`06-ai-engine.md`) and Semantic Search (`05-frontend-specification.md` → Knowledge Base module), retrieval is broader (school-wide or subject-wide) since the user's query itself defines scope.

## Seeding the Competency Taxonomy

Before any school processes its first book, the `competencies` table must be pre-seeded with the official PARAKH/NAS competency framework (per grade band and subject, as published by PARAKH) — this is reference data shipped with the application, not something the AI invents per school. Implementation should include a seed script (`scripts/seed_competencies.py` or an Alembic data migration) that loads this from a bundled JSON/CSV file. **Sourcing this competency list accurately from official PARAKH/NAS documentation is a hard prerequisite for the Competency Mapping Agent to function correctly** — treat acquiring this reference data as a Phase 3 blocker (see `19-roadmap.md`), not an afterthought.

## RAG-grounded prompt assembly pattern

Every generative prompt in `20-ai-prompt-library.md` follows this shape:

```
[SYSTEM] Role + constraints (e.g., "You are a curriculum assistant for GSEB Grade {grade} {subject}. Only use the provided context. Respond in valid JSON matching this schema: {...}")

[CONTEXT] Retrieved chunks, clearly delimited:
---
Source chunk 1 (Chapter: {chapter_title}, Topic: {topic_title}):
{chunk_text}
---
Source chunk 2: ...
---

[TASK] The specific instruction (extract concepts / generate a question / etc.)
```

This separation (system role, retrieved context, task instruction) is consistent across all agents so prompt templates can share a common assembly function (`build_prompt(system, context_chunks, task)` in `services/ai_pipeline/prompt_builder.py`) instead of each agent hand-formatting strings independently.

## Re-indexing and updates

- If a teacher edits/replaces an uploaded book, re-run the full pipeline for that `book_id` from the Document Agent stage, and **delete the old Chroma vectors for that book first** (by metadata filter `where={"book_id": book_id}`) before re-ingesting, to avoid stale duplicate chunks polluting retrieval.
- Deleting a book should cascade-delete its `knowledge_chunks` rows and corresponding Chroma vectors together (same atomicity concern as ingestion).

## Evaluating retrieval quality (lightweight, not a full eval harness for v1)

When implementing, sanity-check retrieval manually for a few known topics per subject: does querying "photosynthesis process steps" against a Grade 8 Science book actually return the photosynthesis chunk and not an unrelated chunk about respiration? This kind of spot-check during Phase 3 (`19-roadmap.md`) is worth doing before building Question Generation on top of retrieval that hasn't been verified to work.
