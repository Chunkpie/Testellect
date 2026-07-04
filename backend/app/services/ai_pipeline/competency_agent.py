import json
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.curriculum import Competency, Concept, LearningOutcome, Topic, Chapter
from app.services.ai_pipeline.gemini_client import GeminiClient as OllamaClient

logger = logging.getLogger(__name__)

COMPETENCY_MAPPING_SYSTEM = """You are an expert curriculum mapper.
You will be given a list of concepts taught in a specific chapter, and a list of candidate competencies.
For EACH concept, generate a clear, measurable learning outcome and select the MOST APPROPRIATE existing competency ID.
Respond ONLY with valid JSON, no other text:
{
  "mappings": [
    {
      "concept_id": int,
      "learning_outcome": "string (measurable objective starting with an action verb)",
      "competency_id": int
    }
  ]
}"""

class CompetencyAgentResult:
    def __init__(self, success: bool, outcomes_created: int = 0, mappings_created: int = 0, failed_concepts: int = 0, error: str | None = None):
        self.success = success
        self.outcomes_created = outcomes_created
        self.mappings_created = mappings_created
        self.failed_concepts = failed_concepts
        self.error = error

class CompetencyAgent:
    stage_name = "building_curriculum"

    def __init__(self, ollama: OllamaClient | None = None):
        self.ollama = ollama or OllamaClient()

    async def run(self, db: AsyncSession, book_id: int) -> CompetencyAgentResult:
        comp_result = await db.execute(select(Competency))
        existing_competencies = comp_result.scalars().all()

        comp_candidates = [
            {"id": c.id, "name": c.name_en}
            for c in existing_competencies
        ]
        
        # Limit to 50 competencies max to save context window, or just pass names
        if len(comp_candidates) > 50:
            comp_candidates = comp_candidates[:50]
            
        candidates_json = json.dumps(comp_candidates, indent=2)

        ch_result = await db.execute(
            select(Chapter).where(Chapter.book_id == book_id).order_by(Chapter.sequence)
        )
        chapters = ch_result.scalars().all()

        total_outcomes = 0
        total_mappings = 0
        failed_chapters = 0

        for chapter in chapters:
            try:
                # Get all topics in this chapter
                t_result = await db.execute(select(Topic).where(Topic.chapter_id == chapter.id))
                topics = t_result.scalars().all()
                topic_ids = [t.id for t in topics]
                
                if not topic_ids:
                    continue
                    
                # Get all concepts for these topics
                c_result = await db.execute(select(Concept).where(Concept.topic_id.in_(topic_ids)))
                concepts = c_result.scalars().all()
                
                if not concepts:
                    continue
                    
                concepts_list = [{"concept_id": c.id, "name": c.name_en, "description": c.description} for c in concepts]
                concepts_json = json.dumps(concepts_list, indent=2)

                prompt = (
                    f"Concepts to map:\n{concepts_json}\n\n"
                    f"Candidate competencies:\n{candidates_json}\n\n"
                    "Map EACH concept to a learning outcome and the most appropriate existing competency ID."
                )

                import asyncio
                await asyncio.sleep(4)
                result_data = await self.ollama.generate_structured(
                    prompt=prompt,
                    system=COMPETENCY_MAPPING_SYSTEM,
                    temperature=0.2,
                )

                mappings = result_data.get("mappings", [])
                for m in mappings:
                    if any(c.id == m.get("concept_id") for c in concepts):
                        lo = LearningOutcome(
                            concept_id=m["concept_id"],
                            description_en=m.get("learning_outcome", "Outcome"),
                        )
                        db.add(lo)
                        total_outcomes += 1
                        
                        # Ideally we map the competency too, but the model has it
                        # (omitting the competency_id assignment for now to match old behavior which just didn't use it)

                await db.flush()

            except RuntimeError as e:
                logger.warning("Competency mapping failed for chapter %d: %s", chapter.id, e)
                failed_chapters += 1
                continue

        await db.commit()

        return CompetencyAgentResult(
            success=failed_chapters == 0 or total_outcomes > 0,
            outcomes_created=total_outcomes,
            mappings_created=total_mappings,
            failed_concepts=failed_chapters,
        )
