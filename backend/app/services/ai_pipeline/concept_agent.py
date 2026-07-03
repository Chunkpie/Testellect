import json
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.curriculum import Chapter, Concept, KnowledgeChunk, Topic
from app.services.ai_pipeline.ollama_client import OllamaClient

logger = logging.getLogger(__name__)

CONCEPT_EXTRACTION_SYSTEM = """You are a curriculum analysis assistant for GSEB textbooks.
You will be given the text of one topic from a textbook chapter. Extract the distinct,
teachable concepts contained in this topic. A concept should be specific enough to generate
a focused assessment question about, not as broad as the whole topic.
Only use the provided text. Respond ONLY with valid JSON, no other text:
{
  "concepts": [
    {"name": "string", "description": "string (1-2 sentences, grounded in the text)"}
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
        failed_topics = 0

        for chapter in chapters:
            t_result = await db.execute(
                select(Topic).where(Topic.chapter_id == chapter.id).order_by(Topic.sequence)
            )
            topics = t_result.scalars().all()

            for topic in topics:
                try:
                    chunks_result = await db.execute(
                        select(KnowledgeChunk)
                        .where(KnowledgeChunk.book_id == book_id)
                        .order_by(KnowledgeChunk.chunk_index)
                    )
                    topic_chunks = chunks_result.scalars().all()

                    if not topic_chunks:
                        continue

                    chunk_texts = "\n\n".join(c.chunk_text for c in topic_chunks[:3])

                    prompt = f"Topic: {topic.title_en}\n\nContent:\n{chunk_texts}\n\nExtract the distinct concepts taught in this topic."

                    result_data = await self.ollama.generate_structured(
                        prompt=prompt,
                        system=CONCEPT_EXTRACTION_SYSTEM,
                        temperature=0.2,
                    )

                    concepts = result_data.get("concepts", [])
                    for c in concepts:
                        concept = Concept(
                            topic_id=topic.id,
                            name_en=c["name"],
                            description=c.get("description", ""),
                            extracted_by="ai",
                        )
                        db.add(concept)
                        total_concepts += 1

                    await db.flush()

                except RuntimeError as e:
                    logger.warning("Concept extraction failed for topic %d (%s): %s", topic.id, topic.title_en, e)
                    failed_topics += 1
                    continue

        await db.commit()

        return ConceptAgentResult(
            success=failed_topics == 0 or total_concepts > 0,
            concepts_created=total_concepts,
            failed_topics=failed_topics,
        )

    async def run_for_topic(self, db: AsyncSession, topic_id: int) -> list[dict]:
        result = await db.execute(select(Topic).where(Topic.id == topic_id))
        topic = result.scalar_one_or_none()
        if not topic:
            return []

        chunks_result = await db.execute(
            select(KnowledgeChunk)
            .where(KnowledgeChunk.chapter_id == topic.chapter_id)
            .order_by(KnowledgeChunk.chunk_index)
        )
        topic_chunks = chunks_result.scalars().all()
        chunk_texts = "\n\n".join(c.chunk_text for c in topic_chunks[:5])

        prompt = f"Topic: {topic.title_en}\n\nContent:\n{chunk_texts}\n\nExtract the distinct concepts taught in this topic."

        try:
            result_data = await self.ollama.generate_structured(
                prompt=prompt,
                system=CONCEPT_EXTRACTION_SYSTEM,
                temperature=0.2,
            )
            return result_data.get("concepts", [])
        except RuntimeError:
            return []
