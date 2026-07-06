import json
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.admin import Job
from app.db.models.curriculum import Book
from app.services.ai_pipeline.gemini_client import GeminiClient as OllamaClient
from app.services.ai_pipeline.document_agent import DocumentAgent
from app.services.ai_pipeline.curriculum_agent import CurriculumAgent
from app.services.ai_pipeline.concept_agent import ConceptAgent
from app.services.ai_pipeline.competency_agent import CompetencyAgent

logger = logging.getLogger(__name__)

PROCESSING_STATUSES = {
    "extracting_text": "extracting_text",
    "building_curriculum": "building_curriculum",
    "extracting_concepts": "extracting_concepts",
    "mapping_competencies": "mapping_competencies",
    "ready": "ready",
    "failed": "failed",
}


class PipelineOrchestrator:
    def __init__(self, ollama: OllamaClient | None = None):
        self.ollama = ollama or OllamaClient()
        self.document_agent = DocumentAgent()
        self.curriculum_agent = CurriculumAgent(self.ollama)
        self.concept_agent = ConceptAgent(self.ollama)
        self.competency_agent = CompetencyAgent(self.ollama)

    async def process_book(
        self,
        db: AsyncSession,
        book_id: int,
        user_id: str | None = None,
        stages: list[str] | None = None,
    ) -> dict:
        result = await db.execute(select(Book).where(Book.id == book_id))
        book = result.scalar_one_or_none()
        if not book:
            return {"success": False, "error": "Book not found"}

        job_id = str(uuid.uuid4())
        job = Job(
            id=job_id,
            type="book_processing",
            status="running",
            params=json.dumps({"book_id": book_id, "stages": stages or ["all"]}),
            created_by=user_id or str(book.uploaded_by or ""),
        )
        db.add(job)
        await db.commit()

        stage_results: dict[str, dict] = {}
        all_success = True

        pipeline_stages = stages or ["document", "curriculum", "concept", "competency"]

        try:
            if "document" in pipeline_stages:
                book.processing_status = "extracting_text"
                await db.commit()
                doc_result = await self.document_agent.run(db, book_id)
                stage_results["document"] = {
                    "success": doc_result.success,
                    "chunks_created": doc_result.chunks_created,
                    "error": doc_result.error,
                }
                if not doc_result.success:
                    all_success = False
                    book.processing_status = "failed"
                    book.processing_error = f"Document Agent: {doc_result.error}"
                    await db.commit()
                    job.status = "failed"
                    job.error = book.processing_error
                    await db.commit()
                    return {"success": False, "job_id": job_id, "stages": stage_results}

            if "curriculum" in pipeline_stages:
                book.processing_status = "building_curriculum"
                await db.commit()
                curr_result = await self.curriculum_agent.run(db, book_id)
                stage_results["curriculum"] = {
                    "success": curr_result.success,
                    "chapters_created": curr_result.chapters_created,
                    "topics_created": curr_result.topics_created,
                    "error": curr_result.error,
                }
                if not curr_result.success:
                    all_success = False
                    book.processing_status = "failed"
                    book.processing_error = f"Curriculum Agent: {curr_result.error}"
                    await db.commit()
                    job.status = "failed"
                    job.error = book.processing_error
                    await db.commit()
                    return {"success": False, "job_id": job_id, "stages": stage_results}

            if "concept" in pipeline_stages:
                book.processing_status = "extracting_concepts"
                await db.commit()
                conc_result = await self.concept_agent.run(db, book_id)
                stage_results["concept"] = {
                    "success": conc_result.success,
                    "concepts_created": conc_result.concepts_created,
                    "failed_topics": conc_result.failed_topics,
                    "error": conc_result.error,
                }
                if not conc_result.success:
                    all_success = False

            if "competency" in pipeline_stages:
                book.processing_status = "mapping_competencies"
                await db.commit()
                comp_result = await self.competency_agent.run(db, book_id)
                stage_results["competency"] = {
                    "success": comp_result.success,
                    "outcomes_created": comp_result.outcomes_created,
                    "mappings_created": comp_result.mappings_created,
                    "failed_concepts": comp_result.failed_concepts,
                    "error": comp_result.error,
                }
                if not comp_result.success:
                    all_success = False

        except Exception as e:
            logger.exception("Pipeline orchestrator error for book %d", book_id)
            await db.rollback()
            all_success = False
            book.processing_status = "failed"
            book.processing_error = f"Pipeline error: {e}"
            db.add(book)
            await db.commit()
            job.status = "failed"
            job.error = str(e)
            db.add(job)
            await db.commit()
            return {"success": False, "job_id": job_id, "stages": stage_results, "error": str(e)}

        book.processing_status = "ready" if all_success else "failed"
        if not all_success:
            errors = []
            for stage, result in stage_results.items():
                if not result.get("success"):
                    errors.append(f"{stage}: {result.get('error', 'unknown error')}")
            book.processing_error = "; ".join(errors)

        job.status = "success" if all_success else "failed"
        job.progress = 100 if all_success else 50
        await db.commit()

        return {
            "success": all_success,
            "job_id": job_id,
            "stages": stage_results,
        }
