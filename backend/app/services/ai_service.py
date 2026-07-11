import asyncio
import json
import logging
import re
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, Boolean
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.curriculum import Book, Chapter, Competency, Concept, KnowledgeChunk, LearningOutcome, LearningOutcomeCompetency, Topic
from app.db.models.questions import QuestionBank, QuestionOption
from app.services.ai_pipeline.ollama_client import OllamaClient
from app.services.ai_pipeline.prompt_builder import build_prompt
from app.services.ai_pipeline.pipeline_orchestrator import PipelineOrchestrator
from app.services.ai_pipeline.retrieval import ChromaDBClient

logger = logging.getLogger(__name__)

QUESTION_GENERATION_SYSTEM = """You are a GSEB assessment expert generating a {question_type} for Grade {grade} students.

Concept: "{concept_name}"
Bloom's Level: "{bloom_level}"
Difficulty: "{difficulty}"
Competency: "{competency_name}"

REQUIREMENTS (strict):
- Write a real-world scenario-based question (NOT definition recall)
- Exactly 4 options with exactly 1 correct answer
- Difficulty must match "{difficulty}" level
- Question text must be self-contained (include the scenario)
- All text MUST be exclusively in {language}
{image_requirement}

CRITICAL: Respond with ONLY a valid JSON object. No markdown, no code fences, no extra text.

VALID JSON EXAMPLE:
{{
  "question_text": "...",
  "options": [
    {{ "text": "...", "is_correct": true }},
    {{ "text": "...", "is_correct": false }},
    {{ "text": "...", "is_correct": false }},
    {{ "text": "...", "is_correct": false }}
  ],
  "explanation": "...",
  "estimated_time_seconds": 60,
  "marks_suggestion": 1{image_tag_example}
}}"""

ASSISTANT_INTENT_SYSTEM = """You are routing a teacher's request to the correct platform capability. Given the teacher's
message, identify which of these intents it matches, and extract the relevant parameters.
If it doesn't clearly match any, use "general_question".
Respond ONLY with valid JSON, no other text:
{
  "intent": "generate_questions|generate_paper|explain_concept|generate_remedial_worksheet|build_blueprint|summarize_chapter|general_question",
  "parameters": {}
}"""

EXPLAIN_CONCEPT_SYSTEM = """You are explaining a curriculum concept to a teacher who wants a clear, accurate explanation
they could use when re-teaching it. Ground your explanation strictly in the provided source
text. Keep it concise (under 200 words) and pedagogically useful — note common student
misconceptions if evident from the text.
Respond ONLY with valid JSON, no other text:
{
  "explanation": "string",
  "common_misconceptions": ["string", ...]
}"""

SUMMARIZE_CHAPTER_SYSTEM = """You are summarizing a textbook chapter for a teacher's quick reference. Ground the summary
strictly in the provided source text. Structure it as a short overview followed by the key
concepts covered, in the order they appear.
Respond ONLY with valid JSON, no other text:
{
  "overview": "string (2-3 sentences)",
  "key_concepts": ["string", ...]
}"""


def _validate_question(data: dict) -> str | None:
    q_text = (data.get("question_text") or "").strip()
    if len(q_text) < 15:
        return f"question_text too short ({len(q_text)} chars, need >= 15)"

    options = data.get("options", [])
    if not isinstance(options, list) or len(options) != 4:
        return f"need exactly 4 options, got {len(options) if isinstance(options, list) else type(options).__name__}"

    texts = [str(o.get("text", "")) if isinstance(o, dict) else str(o) for o in options]
    if any(len(t) < 1 for t in texts):
        return "one or more option texts are empty"
    if len(set(t.lower() for t in texts)) < len(texts):
        return "duplicate option texts detected"

    correct = sum(1 for o in options if isinstance(o, dict) and o.get("is_correct"))
    if correct != 1:
        return f"need exactly 1 correct option, got {correct}"

    return None


def _extract_options(options_raw: Any) -> list[dict]:
    result = []
    if not isinstance(options_raw, list):
        return result
    for opt in options_raw:
        if isinstance(opt, dict):
            result.append({
                "text": str(opt.get("text", "")),
                "is_correct": bool(opt.get("is_correct", False)),
            })
        else:
            result.append({"text": str(opt), "is_correct": False})
    return result


def _normalise_one_correct(options: list[dict]) -> list[dict]:
    correct = [o for o in options if o["is_correct"]]
    if len(correct) == 1:
        return options
    if not correct and options:
        options[0]["is_correct"] = True
        return options
    if len(correct) > 1:
        for o in options[1:]:
            o["is_correct"] = False
    return options


class AiService:
    def __init__(self, ollama: OllamaClient | None = None):
        self.ollama = ollama or OllamaClient()
        self.orchestrator = PipelineOrchestrator(self.ollama)
        self.chromadb = ChromaDBClient(ollama=self.ollama)

    async def _resolve_concept_context(
        self, db: AsyncSession, concept_id: int
    ) -> tuple[int, str, str, str, list[dict[str, Any]]]:
        result = await db.execute(select(Concept).where(Concept.id == concept_id))
        concept = result.scalar_one_or_none()
        if not concept:
            raise ValueError(f"Concept {concept_id} not found")

        topic = None
        chapter = None
        book = None
        grade = 0
        if concept.topic_id:
            t_result = await db.execute(select(Topic).where(Topic.id == concept.topic_id))
            topic = t_result.scalar_one_or_none()
            if topic and topic.chapter_id:
                ch_result = await db.execute(select(Chapter).where(Chapter.id == topic.chapter_id))
                chapter = ch_result.scalar_one_or_none()
                if chapter and chapter.book_id:
                    b_result = await db.execute(select(Book).where(Book.id == chapter.book_id))
                    book = b_result.scalar_one_or_none()
                    if book:
                        grade = book.grade

        lo_result = await db.execute(
            select(LearningOutcome).where(LearningOutcome.concept_id == concept_id)
        )
        learning_outcome = lo_result.scalars().first()

        competency_name = "general"
        if learning_outcome:
            comp_result = await db.execute(
                select(Competency)
                .join(LearningOutcomeCompetency)
                .where(LearningOutcomeCompetency.c.learning_outcome_id == learning_outcome.id)
            )
            competency = comp_result.scalars().first()
            if competency:
                competency_name = competency.name_en

        context_list = [
            {
                "text": f"Concept: {concept.name_en}", 
                "chapter_title": chapter.title_en if chapter else "", 
                "topic_title": topic.title_en if topic else ""
            }
        ]

        return grade, concept.name_en, competency_name, context_list

    async def _generate_single_question(
        self,
        system_prompt: str,
        context_list: list[dict],
        task: str,
        retry_count: int = 0,
    ) -> dict | None:
        max_retries = 3 - retry_count
        for attempt in range(max_retries):
            temp_variants = [0.1, 0.3, 0.5]
            temperature = temp_variants[min(attempt, len(temp_variants) - 1)]
            task_variant = task
            if attempt == 1:
                task_variant += " IMPORTANT: Return ONLY valid JSON. No markdown."
            elif attempt == 2:
                task_variant = "Generate ONE MCQ. Respond with raw JSON only: {\"question_text\": \"...\", \"options\": [{\"text\": \"...\", \"is_correct\": false}], \"explanation\": \"...\"}"
            try:
                sp, prompt = build_prompt(system_prompt, context_list, task_variant)
                result = await self.ollama.generate_structured(
                    prompt=prompt, system=sp, temperature=temperature, max_retries=15,
                )
                error = _validate_question(result)
                if error:
                    logger.warning("Validation failed (attempt %d): %s — raw keys=%s", attempt + 1, error, list(result.keys()))
                    continue
                return result
            except Exception as e:
                logger.warning("Generation failed (attempt %d): %s", attempt + 1, str(e)[:120])
                continue
        return None

    async def generate_questions_batched(
        self,
        db: AsyncSession,
        concept_id: int,
        total_count: int = 50,
        batch_size: int | None = None,
        bloom_level: str = "understand",
        difficulty: str = "medium",
        question_type: str = "mcq",
        language: str = "English",
        school_id: int | None = None,
        on_progress: Callable | None = None,
    ) -> list[dict[str, Any]]:
        batch_size = batch_size or settings.OLLAMA_BATCH_SIZE
        grade, concept_name, competency_name, context_list = await self._resolve_concept_context(db, concept_id)

        all_questions: list[dict[str, Any]] = []

        image_requirement = "- DO NOT use or refer to any pictures, graphs, diagrams, or images in the question. The question must be entirely text-based and self-contained."
        image_tag_example = ""

        system_prompt = QUESTION_GENERATION_SYSTEM.format(
            question_type=question_type,
            grade=grade,
            concept_name=concept_name,
            bloom_level=bloom_level,
            difficulty=difficulty,
            competency_name=competency_name,
            language=language,
            image_requirement=image_requirement,
            image_tag_example=image_tag_example,
        )
        task = f"Generate exactly {{current_batch}} {question_type} questions in {language} as specified above. Return a JSON array of these objects."

        q_idx = 0
        while len(all_questions) < total_count:
            remaining = total_count - len(all_questions)
            current_batch = min(batch_size, remaining)

            task_batch = task.format(current_batch=current_batch)
            if all_questions:
                existing_texts = [q.get("question_text", "") for q in all_questions if q.get("question_text")]
                if existing_texts:
                    task_batch += "\n\nCRITICAL: DO NOT repeat any of the following questions or concepts:\n"
                    for ext in existing_texts[-10:]: # Limit to last 10 to save tokens
                        task_batch += f"- {ext[:100]}...\n"

            coros = [
                self._generate_single_question(system_prompt, context_list, task_batch)
                # Just one call per batch
            ]
            results = await asyncio.gather(*coros, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    logger.warning("Batch unhandled exception: %s", str(result)[:120])
                    continue
                if result is None:
                    logger.warning("Batch failed after all retries")
                    continue

                items = result.get("items", [result]) if isinstance(result, dict) else result
                if not isinstance(items, list):
                    items = [items]

                for item in items:
                    if len(all_questions) >= total_count:
                        break
                    
                    q_idx += 1
                    q_text = (item.get("question_text") or "").strip()
                    if not q_text:
                        logger.warning("Question %d: empty question_text", q_idx)
                        continue

                    option_objects = _normalise_one_correct(_extract_options(item.get("options", [])))
                    if len(option_objects) < 2:
                        logger.warning("Question %d: insufficient valid options (%d)", q_idx, len(option_objects))
                        continue

                    lang_lower = language.lower()
                    
                    image_asset_id = None
                    image_tag = item.get("image_tag")
                    if image_tag and school_id:
                        from app.db.models.image_bank import ImageAsset
                        img_result = await db.execute(
                            select(ImageAsset).where(
                                ImageAsset.school_id == school_id,
                                ImageAsset.tags.ilike(f"%{image_tag}%")
                            ).limit(1)
                        )
                        img = img_result.scalar_one_or_none()
                        if img:
                            image_asset_id = img.id

                    question = QuestionBank(
                        school_id=school_id or 0,
                        concept_id=concept_id,
                        question_text_en=q_text if lang_lower == "english" else "",
                        question_text_hi=q_text if lang_lower == "hindi" else "",
                        question_text_gu=q_text if lang_lower == "gujarati" else "",
                        question_type=question_type or "mcq",
                        bloom_level=bloom_level,
                        difficulty=difficulty,
                        marks=1.0,
                        estimated_time_seconds=item.get("estimated_time_seconds", 60),
                        explanation_en=item.get("explanation", "") if lang_lower == "english" else "",
                        explanation_hi=item.get("explanation", "") if lang_lower == "hindi" else "",
                        explanation_gu=item.get("explanation", "") if lang_lower == "gujarati" else "",
                        image_asset_id=image_asset_id,
                        generated_by="ai",
                        approval_status="APPROVED",
                    )
                    db.add(question)
                    await db.flush()

                    for seq, opt in enumerate(option_objects):
                        db.add(QuestionOption(
                            question_id=question.id,
                            option_text_en=opt["text"] if lang_lower == "english" else "",
                            option_text_hi=opt["text"] if lang_lower == "hindi" else "",
                            option_text_gu=opt["text"] if lang_lower == "gujarati" else "",
                            is_correct=opt["is_correct"],
                            sequence=seq,
                        ))

                    all_questions.append({
                        "id": question.id,
                        "question_text": q_text,
                        "options": option_objects,
                        "explanation": item.get("explanation", ""),
                        "bloom_level": bloom_level,
                        "difficulty": difficulty,
                    })

            # Commit batch
            try:
                await db.commit()
            except Exception:
                await db.rollback()
                logger.error("Batch commit failed, rolling back %d questions", len(all_questions) - len([r for r in results if r is not None and not isinstance(r, Exception)]))
                continue

            progress = len(all_questions)
            logger.info("Batch complete: %d/%d questions saved (batch=%d)", progress, total_count, current_batch)
            if on_progress:
                await on_progress(progress, total_count, (progress // batch_size) + 1, -1)

        return all_questions

    async def generate_questions(
        self,
        db: AsyncSession,
        concept_id: int,
        count: int = 5,
        bloom_level: str = "understand",
        difficulty: str = "medium",
        question_type: str = "mcq",
        school_id: int | None = None,
    ) -> list[dict[str, Any]]:
        grade, concept_name, competency_name, context_list = await self._resolve_concept_context(db, concept_id)

        image_requirement = ""
        image_tag_example = ""
        if grade <= 5:
            image_requirement = "- The question should reference a visual image. Include an 'image_tag' field with a single word (e.g. 'cat', 'triangle', 'mango') describing the required image."
            image_tag_example = ',\n  "image_tag": "apple"'

        system_prompt = QUESTION_GENERATION_SYSTEM.format(
            question_type=question_type,
            grade=grade,
            concept_name=concept_name,
            bloom_level=bloom_level,
            difficulty=difficulty,
            competency_name=competency_name,
            language="English",
            image_requirement=image_requirement,
            image_tag_example=image_tag_example,
        )

        task = f"Generate one {question_type} question as specified above."

        questions: list[dict[str, Any]] = []
        for _ in range(count):
            try:
                system, prompt = build_prompt(system_prompt, context_list, task)
                result_data = await self.ollama.generate_structured(
                    prompt=prompt,
                    system=system,
                )
                questions.append({
                    "question_text": result_data.get("question_text", ""),
                    "options": result_data.get("options", []),
                    "explanation": result_data.get("explanation", ""),
                    "estimated_time_seconds": result_data.get("estimated_time_seconds", 60),
                    "marks_suggestion": result_data.get("marks_suggestion", 1),
                    "concept_id": concept_id,
                    "bloom_level": bloom_level,
                    "difficulty": difficulty,
                    "question_type": question_type,
                })
            except RuntimeError as e:
                logger.warning("Question generation failed: %s", e)
                continue

        return questions

    async def analyze_book(
        self,
        db: AsyncSession,
        book_id: int,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        return await self.orchestrator.process_book(db, book_id, user_id)

    async def extract_text_only(
        self,
        db: AsyncSession,
        book_id: int,
    ) -> dict[str, Any]:
        from app.services.ai_pipeline.document_agent import DocumentAgent
        agent = DocumentAgent()
        result = await agent.run(db, book_id)
        return {
            "success": result.success,
            "chunks_created": result.chunks_created,
            "error": result.error,
        }

    async def chat_assistant(
        self,
        db: AsyncSession,
        message: str,
        school_id: int | None = None,
        conversation_id: str | None = None,
    ) -> dict[str, Any]:
        try:
            routing_result = await self.ollama.generate_structured(
                prompt=f'Route this teacher message: "{message}"',
                system=ASSISTANT_INTENT_SYSTEM,
            )
        except RuntimeError:
            routing_result = {"intent": "general_question", "parameters": {}}

        intent = routing_result.get("intent", "general_question")
        params = routing_result.get("parameters", {})

        if intent == "explain_concept":
            concept_name = params.get("concept_name", "")
            if concept_name and school_id:
                chunks = await self.chromadb.retrieve(
                    school_id=school_id,
                    query=concept_name,
                    top_k=3,
                )
                context_list = [{"text": c["text"], "chapter_title": c["metadata"].get("chapter_title", ""), "topic_title": ""} for c in chunks]
                system, prompt = build_prompt(EXPLAIN_CONCEPT_SYSTEM, context_list, f'Explain the concept "{concept_name}" for a teacher\'s reference.')
                try:
                    result_data = await self.ollama.generate_structured(prompt=prompt, system=system)
                    return {
                        "reply": result_data.get("explanation", ""),
                        "misconceptions": result_data.get("common_misconceptions", []),
                        "intent": intent,
                        "conversation_id": conversation_id,
                    }
                except RuntimeError as e:
                    return {"reply": f"Could not explain concept: {e}", "intent": intent, "conversation_id": conversation_id}

        if intent == "summarize_chapter":
            chapter_name = params.get("chapter_name", "")
            if chapter_name and school_id:
                chunks = await self.chromadb.retrieve(
                    school_id=school_id,
                    query=chapter_name,
                    top_k=10,
                )
                context_list = [{"text": c["text"], "chapter_title": "", "topic_title": ""} for c in chunks]
                system, prompt = build_prompt(SUMMARIZE_CHAPTER_SYSTEM, context_list, "Summarize this chapter for a teacher.")
                try:
                    result_data = await self.ollama.generate_structured(prompt=prompt, system=system)
                    return {
                        "reply": result_data.get("overview", ""),
                        "key_concepts": result_data.get("key_concepts", []),
                        "intent": intent,
                        "conversation_id": conversation_id,
                    }
                except RuntimeError as e:
                    return {"reply": f"Could not summarize chapter: {e}", "intent": intent, "conversation_id": conversation_id}

        return {
            "reply": f"I can help you with generating questions, explaining concepts, summarizing chapters, and more. You said: {message}",
            "intent": intent,
            "conversation_id": conversation_id,
        }

    async def generate_and_create_papers(
        self,
        db: AsyncSession,
        book_id: int,
        user_id: int,
        school_id: int | None = None,
        total_questions: int = 150,
        num_papers: int = 15,
        questions_per_paper: int = 40,
    ) -> None:
        from app.services.paper_generator import create_blueprint_and_papers
        
        # 1. Fetch all concepts for this book
        concepts_result = await db.execute(
            select(Concept)
            .join(Concept.topic)
            .join(Topic.chapter)
            .where(Chapter.book_id == book_id)
        )
        concepts = concepts_result.scalars().all()
        if not concepts:
            logger.error(f"No concepts found for book {book_id}")
            return
            
        import random
        random.shuffle(concepts)
        
        # 2. Loop and generate questions
        generated_questions = []
        for i in range(total_questions):
            c = concepts[i % len(concepts)]
            logger.info(f"Generating question {i+1}/{total_questions} from concept: {c.name_en}")
            
            # Use generate_questions_batched to automatically save to DB
            try:
                # We fetch the exact DB object since generate_questions_batched returns dicts
                # But it actually commits them. Let's just grab all questions for this book after generation.
                await self.generate_questions_batched(
                    db=db,
                    concept_id=c.id,
                    total_count=1,
                    batch_size=1,
                    school_id=school_id
                )
            except Exception as e:
                logger.error(f"Error generating question for concept {c.id}: {e}")

        logger.info("Questions generated. Fetching all questions for this book to create papers...")
        # Fetch the newly generated questions for this book
        q_res = await db.execute(
            select(QuestionBank)
            .join(QuestionBank.concept)
            .join(Concept.topic)
            .join(Topic.chapter)
            .where(Chapter.book_id == book_id)
            .order_by(QuestionBank.created_at.desc())
            .limit(total_questions * 2) # Get recent
        )
        all_book_qs = q_res.scalars().all()
        
        if len(all_book_qs) >= questions_per_paper:
            await create_blueprint_and_papers(
                db=db,
                book_id=book_id,
                user_id=user_id,
                school_id=school_id or 0,
                questions=all_book_qs,
                num_papers=num_papers,
                questions_per_paper=questions_per_paper
            )
        else:
            logger.error("Not enough questions generated to create papers")
