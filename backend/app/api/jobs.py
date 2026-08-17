from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.models.models import User, Job

router = APIRouter()


@router.get("/{job_id}")
async def get_job_status(job_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        return {"error": "Job not found"}
    return {
        "id": job.id,
        "type": job.type,
        "status": job.status or "unknown",
        "progress": job.progress,
        "error": job.error,
    }


@router.get("")
async def list_jobs(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Job).order_by(Job.created_at.desc()).limit(20))
    jobs = result.scalars().all()
    return jobs
