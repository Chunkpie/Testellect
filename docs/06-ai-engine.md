# 06 — AI Engine

## Purpose

This document specifies how the platform talks to the local LLM (Ollama running Qwen3 8B), the contract every AI Pipeline agent must follow, and how the AI Teacher Assistant feature works. It complements `07-rag-architecture.md` (how retrieval feeds these agents) and `20-ai-prompt-library.md` (the actual prompt text to use).

## Core principle, repeated because it's load-bearing

**The system never generates questions directly from raw PDF text.** Every generation step is grounded in the structured curriculum knowledge graph (concepts, learning outcomes, competencies) plus retrieved chunks from ChromaDB — never a raw "summarize this PDF and make 10 questions" call. This is what makes output competency-tagged and traceable, and it's what the whole Document→Curriculum→Concept→Competency→Question agent chain in `02-system-architecture.md` exists to produce.

## Connecting to Ollama

```python
# services/ai_pipeline/ollama_client.py (conceptual)
import httpx

class OllamaClient:
    def __init__(self, base_url: str, model: str, timeout_seconds: int = 120):
        self.base_url = base_url
        self.model = model
        self.timeout = httpx.Timeout(timeout_seconds)

    async def generate(self, prompt: str, system: str | None = None,
                        json_mode: bool = False, temperature: float = 0.3) -> str:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/api/generate", json={
                "model": self.model,
                "prompt": prompt,
                "system": system,
                "format": "json" if json_mode else None,
                "stream": False,
                "options": {"temperature": temperature},
            })
            response.raise_for_status()
            return response.json()["response"]
```

- Use Ollama's `format: "json"` mode for every agent that needs structured output (which is nearly all of them) — this constrains the model to emit valid JSON, which is far more reliable than asking nicely in the prompt and hoping.
- Keep `temperature` low (0.2–0.4) for extraction/classification tasks (concept extraction, competency mapping, quality scoring) where consistency matters more than creativity; allow a slightly higher temperature (0.5–0.7) for question-text generation where some lexical variety across questions is desirable.

## Agent Pipeline Contracts

Every agent in the pipeline (`02-system-architecture.md`) implements the same shape, so the job runner (`04-backend-specification.md` → "Background Jobs") can treat them uniformly:

```python
class PipelineAgent(Protocol):
    stage_name: str

    async def run(self, db: AsyncSession, job_payload: dict) -> AgentResult:
        """
        Reads whatever it needs from the DB (never relies on in-memory state
        from a previous agent). Writes its output directly to the DB.
        Returns AgentResult(success: bool, output_summary: dict, error: str | None).
        Must be safely re-runnable: re-running a completed stage should not
        create duplicate rows (use upsert-by-natural-key or a guard check).
        """
```

### 1. Document Agent
- Input: `book_id`.
- Extracts raw text from the PDF at `books.file_path` (use `pdfplumber` for text-layer PDFs; fall back to OCR via `pytesseract` if a page has no extractable text layer — GSEB textbook scans are sometimes image-only).
- Cleans text: strip headers/footers/page numbers via regex heuristics, normalize whitespace, fix common OCR artifacts.
- Output: cleaned full text persisted (e.g., to a temp file or a staging table) for the Curriculum Agent to consume. Updates `books.processing_status = 'extracting_text'` → done.

### 2. Curriculum Agent
- Input: cleaned text from stage 1.
- Segments by detected headings (font-size/structure heuristics from `pdfplumber`'s layout info where available) into Unit/Chapter/Topic candidates; uses the LLM (see `20-ai-prompt-library.md` → "Curriculum Segmentation Prompt") to confirm/clean up boundaries and titles when heuristics are ambiguous.
- Writes `chapters` and `topics` rows.
- Also chunks the cleaned text into semantically coherent pieces (target ~300–500 tokens per chunk, with small overlap) and writes `knowledge_chunks` rows; sends each chunk to ChromaDB for embedding (see `07-rag-architecture.md`).

### 3. Concept Extraction Agent
- Input: each `topic_id` from stage 2, plus its associated `knowledge_chunks`.
- Prompts the LLM per topic (grounded in that topic's actual chunk text) to extract discrete concepts (see `20-ai-prompt-library.md` → "Concept Extraction Prompt").
- Writes `concepts` rows with `extracted_by = 'ai'`.

### 4. Competency Mapping Agent
- Input: each `concept_id` from stage 3.
- Prompts the LLM, grounded in the concept's description and retrieved similar chunks, to propose a learning outcome and map it to one or more competencies from the existing `competencies` table (a fixed, pre-seeded PARAKH-aligned list — see `07-rag-architecture.md` → "Seeding the Competency Taxonomy"). The agent should **select from existing competencies first**, only proposing a new competency if genuinely nothing fits (flagged for admin review, not auto-created silently).
- Writes `learning_outcomes` and `learning_outcome_competencies` rows.

### 5. Question Generation Agent
Covered in depth in `08-question-engine.md`. Briefly: takes a `(concept_id, competency_id, bloom_level, difficulty, question_type)` tuple (requested by either the teacher directly or the Blueprint/Paper flow needing more bank coverage), retrieves grounding chunks via RAG, and generates one or more candidate questions via the LLM (see `20-ai-prompt-library.md` → "Question Generation Prompt").

### 6. Question Validation Agent
Covered in `08-question-engine.md` → "AI Quality Control". Scores each generated question on concept accuracy, Bloom classification correctness, difficulty, competency coverage, duplicate risk, and language quality, writing `confidence_score`/`duplicate_score` and setting `approval_status = 'pending_review'` (never `'approved'` — that requires a human, see `01-project-overview.md`).

## Timeouts and Retries

- Every Ollama call has an explicit timeout (suggested default: 120s for generation calls, 60s for classification/scoring calls — tune based on observed hardware performance).
- On timeout or malformed JSON response, retry up to 2 times with the same prompt before marking that specific unit of work (one topic, one concept, one question request) as failed — **failure is scoped to that unit, not the whole book/job.** A book with 40 topics where 2 topics fail concept extraction should still have 38 topics with concepts, and the 2 failures should be visible/retriable individually in the UI, not force a full book reprocess.
- Log every failure's prompt + raw response to `ai_analysis.raw_llm_output` (per `03-database-schema.md`) for debugging — this is essential for diagnosing prompt issues against a local model that may behave less predictably than a large hosted model.

## Degrading gracefully on weak hardware

- If Ollama responses are consistently slow (e.g., p95 latency over some threshold like 90s for a single question generation call), the backend should batch fewer concurrent AI jobs (a simple semaphore limiting concurrent in-flight Ollama calls, e.g., max 1–2 concurrent on a CPU-only box) rather than queuing unboundedly and starving the rest of the app.
- Surface processing time expectations in the UI ("This may take a few minutes on this device") rather than implying real-time responsiveness.

## AI Teacher Assistant

A conversational feature (`ai.py` router, e.g. `POST /api/v1/ai/assistant/chat`) that lets teachers ask for: generating question papers, creating competency-based questions, explaining concepts, generating remedial worksheets, building assessment blueprints, and summarizing chapters — all grounded in that school's own knowledge base via RAG (same ChromaDB instance, same competency taxonomy), never a generic open-ended chatbot disconnected from the curriculum data. Each of these "intents" should map to one of the existing pipeline capabilities under the hood (e.g., "generate a remedial worksheet for fractions" reuses the Question Generation Agent scoped to the "fractions" concept plus a worksheet-formatting step) rather than being a separate, unstructured free-text generation path — this keeps assistant output subject to the same quality scoring and human-approval gate as everything else.

## What NOT to do

- Don't let any agent call out to a hosted API as a fallback "in case Ollama is slow" — this would silently violate the offline/no-paid-API constraint. If Ollama is unreachable, fail the job clearly and let the user retry once it's back up.
- Don't auto-approve anything, ever, regardless of confidence score — confidence/duplicate scores inform the teacher's review UI, they don't bypass it.
- Don't regenerate the entire curriculum knowledge graph from scratch when only a few topics fail — re-run only the failed units (see "Timeouts and Retries" above).
