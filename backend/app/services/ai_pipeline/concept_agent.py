import json
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.curriculum import Chapter, Concept, KnowledgeChunk, Topic
from app.services.ai_pipeline.gemini_client import GeminiClient as OllamaClient

logger = logging.getLogger(__name__)

CONCEPT_EXTRACTION_SYSTEM = """You are a curriculum analysis assistant for GSEB textbooks.
You will be given the text of a textbook chapter and a list of topics in that chapter.
Extract 1-3 distinct, teachable concepts for EACH topic. A concept should be specific enough to generate
a focused assessment question about, not as broad as the whole topic.
Only use the provided text. Respond ONLY with valid JSON, no other text:
{
  "concepts": [
    {
      "topic_id": int,
      "name": "string",
      "description": "string (1-2 sentences, grounded in the text)"
    }
  ]
}"""

class ConceptAgentResult:
    def __init__(self, success: bool, concepts_created: int = 0, failed_topics: int = 0, error: str | None = None):
        self.success = success
        self.concepts_created = concepts_created
        self.failed_topics = failed_topics
        self.error = error

class ConceptAgent:
    stage_name = "extracting_concepts"

    def __init__(self, ollama: OllamaClient | None = None):
        self.ollama = ollama or OllamaClient()

    async def run(self, db: AsyncSession, book_id: int) -> ConceptAgentResult:
        ch_result = await db.execute(
            select(Chapter).where(Chapter.book_id == book_id).order_by(Chapter.sequence)
        )
        chapters = ch_result.scalars().all()

        total_concepts = 0
        failed_chapters = 0

        for chapter in chapters:
            try:
                t_result = await db.execute(
                    select(Topic).where(Topic.chapter_id == chapter.id).order_by(Topic.sequence)
                )
                topics = t_result.scalars().all()

                if not topics:
                    continue

                chunks_result = await db.execute(
                    select(KnowledgeChunk)
                    .where(KnowledgeChunk.chapter_id == chapter.id)
                    .order_by(KnowledgeChunk.chunk_index)
                )
                chapter_chunks = chunks_result.scalars().all()
                chunk_texts = "\n\n".join(c.chunk_text for c in chapter_chunks)
                
                # Limit chunk size to avoid massive prompts if the chapter is huge
                if len(chunk_texts) > 25000:
                    chunk_texts = chunk_texts[:25000] + "\n...[truncated]"

                topics_list = [{"topic_id": t.id, "title": t.title_en} for t in topics]
                topics_json = json.dumps(topics_list, indent=2)

                prompt = (
                    f"Chapter Content:\n{chunk_texts}\n\n"
                    f"Topics in this chapter:\n{topics_json}\n\n"
                    "Extract 1-3 distinct concepts for EACH topic in the chapter."
                )

                import asyncio
                await asyncio.sleep(4)
                result_data = await self.ollama.generate_structured(
                    prompt=prompt,
                    system=CONCEPT_EXTRACTION_SYSTEM,
                    temperature=0.2,
                )

                concepts = result_data.get("concepts", [])
                for c in concepts:
                    # Validate topic_id belongs to this chapter
                    if any(t.id == c.get("topic_id") for t in topics):
                        concept = Concept(
                            topic_id=c["topic_id"],
                            name_en=c.get("name", "Unknown Concept"),
                            description=c.get("description", ""),
                            extracted_by="ai",
                        )
                        db.add(concept)
                        total_concepts += 1

                await db.flush()

            except RuntimeError as e:
                logger.warning("Concept extraction failed for chapter %d (%s): %s", chapter.id, chapter.title_en, e)
                failed_chapters += 1
                continue

        await db.commit()

        return ConceptAgentResult(
            success=failed_chapters == 0 or total_concepts > 0,
            concepts_created=total_concepts,
            failed_topics=failed_chapters,
        )

    async def run_for_topic(self, db: AsyncSession, topic_id: int) -> list[dict]:
        return []
