import asyncio
import json
import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.core.audit import log_audit_entry
from app.models.models import User, Job

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory store for active generation tasks
_active_jobs: dict[str, asyncio.Task] = {}


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


@router.post("/assistant/chat")
async def assistant_chat(
    data: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "teacher":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only teachers can use the AI assistant")

    try:
        from app.services.ai_service import AiService
        ai = AiService()
        response = await ai.chat_assistant(
            db=db,
            message=data.message,
            school_id=current_user.school_id,
            conversation_id=data.conversation_id,
        )
    except Exception as e:
        response = {"reply": f"AI Service not available. You said: {data.message}", "conversation_id": data.conversation_id, "error": str(e)}

    return response


class BatchGenerateRequest(BaseModel):
    concept_ids: list[int] | None = None
    competency_id: int | None = None
    bloom_level: str = "understand"
    difficulty: str = "medium"
    question_type: str = "mcq"
    total_count: int = 50
    batch_size: int = 5
    language: str = "English"


@router.post("/generate-questions", status_code=status.HTTP_202_ACCEPTED)
async def start_batch_generation(
    data: BatchGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "teacher":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only teachers can generate questions")

    concept_ids = data.concept_ids or []

    if not concept_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one concept_id is required")

    job_id = str(uuid.uuid4())
    job = Job(
        id=job_id,
        type="question_generation",
        status="queued",
        params=json.dumps({
            "concept_ids": concept_ids,
            "bloom_level": data.bloom_level,
            "difficulty": data.difficulty,
            "question_type": data.question_type,
            "total_count": data.total_count,
            "batch_size": data.batch_size,
            "language": data.language,
        }),
        progress=0,
        created_by=str(current_user.id),
    )
    db.add(job)
    await db.commit()

    await log_audit_entry(
        db=db, user_id=current_user.id, school_id=current_user.school_id,
        action="generate_questions", resource_type="ai_job",
        resource_id=job_id,
        extra_data={"concept_ids": concept_ids, "total_count": data.total_count},
    )

    logger.info("Starting background task for job %s with concept_ids=%s", job_id, concept_ids)
    task = asyncio.create_task(
        _run_batch_generation(
            job_id=job_id,
            concept_ids=concept_ids,
            bloom_level=data.bloom_level,
            difficulty=data.difficulty,
            question_type=data.question_type,
            total_count=data.total_count,
            batch_size=data.batch_size,
            language=data.language,
            school_id=current_user.school_id,
        )
    )
    _active_jobs[job_id] = task

    return {"job_id": job_id, "status": "queued", "message": f"Question generation enqueued. Total: {data.total_count} questions in batches of {data.batch_size}."}


@router.get("/generate-questions/{job_id}")
async def get_generation_job_status(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("teacher", "administrator"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    await db.refresh(job)
    params = json.loads(job.params) if job.params else {}
    is_running = job_id in _active_jobs and not _active_jobs[job_id].done()

    return {
        "id": job.id,
        "type": job.type,
        "status": job.status,
        "progress": job.progress or 0,
        "total": params.get("total_count", 50),
        "error": job.error,
        "is_running": is_running,
    }


@router.get("/generate-questions/{job_id}/stream")
async def stream_generation_progress(
    job_id: str,
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("teacher", "administrator"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    from app.core.database import async_session_factory

    async def event_stream():
        async with async_session_factory() as sse_db:
            result = await sse_db.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                yield f"data: {json.dumps({'error': 'Job not found'})}\n\n"
                return

            total = json.loads(job.params).get("total_count", 50) if job.params else 50
            last_progress = -1

            while True:
                await sse_db.refresh(job)
                progress = job.progress or 0
                status = job.status
                error = job.error

                if progress != last_progress or status in ("completed", "failed"):
                    data = {
                        "progress": progress,
                        "total": total,
                        "status": status,
                        "error": error,
                    }
                    yield f"data: {json.dumps(data)}\n\n"
                    last_progress = progress

                if status == "completed":
                    yield f"data: {json.dumps({'progress': total, 'total': total, 'status': 'completed'})}\n\n"
                    break

                if status == "failed":
                    break

                await asyncio.sleep(1)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _run_batch_generation(
    job_id: str,
    concept_ids: list[int],
    bloom_level: str,
    difficulty: str,
    question_type: str,
    total_count: int,
    batch_size: int,
    language: str,
    school_id: int | None,
):
    from app.core.database import async_session_factory
    from app.services.ai_service import AiService

    logger.info("_run_batch_generation started for job %s", job_id)

    try:
        async with async_session_factory() as db:
            logger.info("Job %s: db session acquired, looking up job", job_id)
            job_result = await db.execute(select(Job).where(Job.id == job_id))
            job = job_result.scalar_one_or_none()
            if job:
                job.status = "processing"
                await db.commit()
                logger.info("Job %s: status set to processing", job_id)

            ai = AiService()
            total_generated = 0

            async def on_progress(progress: int, total: int, batch: int, batches: int, error: str | None = None):
                nonlocal total_generated
                total_generated = progress
                job_result = await db.execute(select(Job).where(Job.id == job_id))
                job = job_result.scalar_one_or_none()
                if job:
                    job.progress = progress
                    if error:
                        job.error = error
                    await db.commit()

            for concept_id in concept_ids:
                questions = await ai.generate_questions_batched(
                    db=db,
                    concept_id=concept_id,
                    total_count=total_count // len(concept_ids) if concept_ids else total_count,
                    batch_size=batch_size,
                    bloom_level=bloom_level,
                    difficulty=difficulty,
                    question_type=question_type,
                    language=language,
                    school_id=school_id,
                    on_progress=on_progress,
                )
                logger.info("Concept %d: generated %d questions", concept_id, len(questions))

            job_result = await db.execute(select(Job).where(Job.id == job_id))
            job = job_result.scalar_one_or_none()
            if job:
                job.status = "completed" if total_generated > 0 else "failed"
                job.progress = total_generated
                if total_generated == 0:
                    job.error = "No questions were generated successfully"
                await db.commit()

    except Exception as e:
        logger.error("Batch generation job %s failed: %s", job_id, str(e))
        try:
            async with async_session_factory() as db:
                job_result = await db.execute(select(Job).where(Job.id == job_id))
                job = job_result.scalar_one_or_none()
                if job:
                    job.status = "failed"
                    job.error = str(e)
                    await db.commit()
        except Exception:
            logger.exception("Failed to update job status for %s", job_id)

    finally:
        _active_jobs.pop(job_id, None)
