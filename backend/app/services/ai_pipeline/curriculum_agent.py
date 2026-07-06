import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.curriculum import Book, Chapter, KnowledgeChunk, Topic
from app.services.ai_pipeline.gemini_client import GeminiClient as OllamaClient

logger = logging.getLogger(__name__)

CURRICULUM_SEGMENTATION_SYSTEM = """You are a curriculum structuring assistant for Gujarat State Education Board (GSEB) textbooks.
You will be given raw extracted text from one section of a textbook, along with heuristically
detected heading candidates. Your job is to confirm or correct the chapter/topic boundaries and
produce clean titles. Only use the text provided. Do not invent content not present in the text.
CRITICAL: You MUST completely IGNORE non-academic frontmatter and backmatter. Do NOT create chapters for "Foreword", "Preface", "Acknowledgements", "Index", "Academic Calendar", "Rationalisation of Content", or other preliminary/concluding sections. ONLY extract actual academic curriculum chapters.
Respond ONLY with valid JSON matching this schema, with no other text:
{
  "chapters": [
    {"title": "string", "unit_name": "string or null", "start_marker": "string (exact text snippet where this chapter begins)"}
  ],
  "topics": [
    {"chapter_title": "string (must match a chapter title above)", "title": "string", "start_marker": "string"}
  ]
}"""


class CurriculumAgentResult:
    def __init__(self, success: bool, chapters_created: int = 0, topics_created: int = 0, error: str | None = None):
        self.success = success
        self.chapters_created = chapters_created
        self.topics_created = topics_created
        self.error = error


class CurriculumAgent:
    stage_name = "building_curriculum"

    def __init__(self, ollama: OllamaClient | None = None):
        self.ollama = ollama or OllamaClient()

    async def run(self, db: AsyncSession, book_id: int) -> CurriculumAgentResult:
        result = await db.execute(select(Book).where(Book.id == book_id))
        book = result.scalar_one_or_none()
        if not book:
            return CurriculumAgentResult(success=False, error=f"Book {book_id} not found")

        chunk_result = await db.execute(
            select(KnowledgeChunk)
            .where(KnowledgeChunk.book_id == book_id)
            .order_by(KnowledgeChunk.chunk_index)
        )
        chunks = chunk_result.scalars().all()
        if not chunks:
            return CurriculumAgentResult(success=False, error="No knowledge chunks found; run Document Agent first")

        full_text = "\n\n".join(c.chunk_text for c in chunks)

        # Try LLM segmentation
        try:
            task = "Confirm or correct the chapter and topic boundaries and titles for the text above."
            text_sample = full_text[:40000] if len(full_text) > 40000 else full_text
            prompt = f"Raw textbook text:\n\n{text_sample}\n\n{task}"
            result_data = await self.ollama.generate_structured(
                prompt=prompt,
                system=CURRICULUM_SEGMENTATION_SYSTEM,
                temperature=0.2,
            )
        except RuntimeError as e:
            logger.warning("LLM segmentation failed, using fallback: %s", e)
            result_data = self._fallback_segmentation(full_text)

        chapters_data = result_data.get("chapters", [])
        topics_data = result_data.get("topics", [])

        chapter_map: dict[str, Chapter] = {}
        for idx, ch_data in enumerate(chapters_data):
            title = ch_data.get("title")
            if not title:
                title = f"Chapter {idx + 1}"
            chapter = Chapter(
                book_id=book_id,
                unit_name=ch_data.get("unit_name"),
                sequence=idx + 1,
                title_en=title,
            )
            db.add(chapter)
            await db.flush()
            chapter_map[ch_data.get("title") or title] = chapter

        topic_count = 0
        for t_data in topics_data:
            chapter_title = t_data.get("chapter_title", "")
            parent = chapter_map.get(chapter_title)
            if not parent:
                continue
            title = t_data.get("title")
            if not title:
                title = f"Topic {topic_count + 1}"
            topic = Topic(
                chapter_id=parent.id,
                sequence=topic_count + 1,
                title_en=title,
            )
            db.add(topic)
            topic_count += 1

        book.processing_status = "building_curriculum"
        await db.commit()

        return CurriculumAgentResult(
            success=True,
            chapters_created=len(chapters_data),
            topics_created=topic_count,
        )

    def _fallback_segmentation(self, text: str) -> dict:
        lines = text.split("\n")
        chapters = []
        topics = []
        chapter_title = "Chapter 1"
        chapters.append({"title": chapter_title, "unit_name": None, "start_marker": lines[0][:80] if lines else ""})
        for i, line in enumerate(lines[:50]):
            stripped = line.strip()
            if stripped and len(stripped) < 100 and stripped.isupper():
                topics.append({"chapter_title": chapter_title, "title": stripped, "start_marker": stripped})
        if not topics:
            topics.append({"chapter_title": chapter_title, "title": lines[0][:60] if lines else "Content", "start_marker": lines[0][:80] if lines else ""})
        return {"chapters": chapters, "topics": topics}
