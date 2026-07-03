import json
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.curriculum import (
    Chapter, Competency, Concept, LearningOutcome,
    LearningOutcomeCompetency, Topic,
)
from app.services.ai_pipeline.ollama_client import OllamaClient

logger = logging.getLogger(__name__)

COMPETENCY_MAPPING_SYSTEM = """You are mapping a curriculum concept to a learning outcome and to one or more competencies
from the official PARAKH/NAS competency framework. You will be given the concept, and a list
of candidate competencies already known to the system for this grade/subject. Prefer selecting
from the candidate list. Only propose a new competency if truly none of the candidates fit, and
mark it "is_new": true in that case so a human can review it.
Respond ONLY with valid JSON, no other text:
{
  "learning_outcome": {"description": "string"},
  "competencies": [
    {"competency_id": "integer or null if new", "name": "string", "is_new": false}
  ]
}"""


class CompetencyAgentResult:
    def __init__(
        self,
        success: bool,
        outcomes_created: int = 0,
        mappings_created: int = 0,
        failed_concepts: int = 0,
        error: str | None = None,
    ):
        self.success = success
        self.outcomes_created = outcomes_created
        self.mappings_created = mappings_created
        self.failed_concepts = failed_concepts
        self.error = error


class CompetencyAgent:
    stage_name = "mapping_competencies"

    def __init__(self, ollama: OllamaClient | None = None):
        self.ollama = ollama or OllamaClient()

    async def run(self, db: AsyncSession, book_id: int) -> CompetencyAgentResult:
        c_result = await db.execute(
            select(Concept)
            .join(Concept.topic)
            .join(Topic.chapter)
            .where(Chapter.book_id == book_id)
        )
        concepts = c_result.scalars().all()

        comp_result = await db.execute(select(Competency))
        existing_competencies = comp_result.scalars().all()

        comp_candidates = [
            {"id": c.id, "name_en": c.name_en, "description": c.description or ""}
            for c in existing_competencies
        ]

        total_outcomes = 0
        total_mappings = 0
        failed = 0

        for concept in concepts:
            try:
                prompt = (
                    f"Concept: {concept.name_en}\n"
                    f"Description: {concept.description or ''}\n\n"
                    f"Candidate competencies:\n{json.dumps(comp_candidates, indent=2)}\n\n"
                    "Map this concept to a learning outcome and the most appropriate existing competency or competencies."
                )

                result_data = await self.ollama.generate_structured(
                    prompt=prompt,
                    system=COMPETENCY_MAPPING_SYSTEM,
                    temperature=0.2,
                )

                lo_raw = result_data.get("learning_outcome", {})
                if isinstance(lo_raw, str):
                    lo_desc = lo_raw
                else:
                    lo_desc = lo_raw.get("description", f"Outcome for {concept.name_en}")
                lo = LearningOutcome(
                    concept_id=concept.id,
                    description_en=lo_desc,
                )
                db.add(lo)
                await db.flush()
                total_outcomes += 1

                for comp in result_data.get("competencies", []):
                    if comp.get("is_new"):
                        continue
                    comp_id = comp.get("competency_id")
                    if comp_id and any(c.id == comp_id for c in existing_competencies):
                        db.execute(
                            LearningOutcomeCompetency.insert().values(
                                learning_outcome_id=lo.id,
                                competency_id=comp_id,
                            )
                        )
                        total_mappings += 1

                await db.flush()

            except RuntimeError as e:
                logger.warning("Competency mapping failed for concept %d (%s): %s", concept.id, concept.name_en, e)
                failed += 1
                continue

        await db.commit()

        return CompetencyAgentResult(
            success=failed == 0 or total_outcomes > 0,
            outcomes_created=total_outcomes,
            mappings_created=total_mappings,
            failed_concepts=failed,
        )
