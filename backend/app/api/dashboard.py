from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.models.models import (
    User,
    Chapter,
    QuestionBank,
    Assessment,
    StudentResult,
    School,
    Student,
)

router = APIRouter()


@router.get("")
async def get_dashboard(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(func.count()).select_from(Chapter))
    total_chapters = result.scalar()

    result = await db.execute(select(func.count()).select_from(QuestionBank))
    total_questions = result.scalar()

    result = await db.execute(select(func.count()).select_from(Assessment))
    total_assessments = result.scalar()

    result = await db.execute(select(func.count()).select_from(StudentResult))
    total_results = result.scalar()

    result = await db.execute(select(func.count()).select_from(School))
    total_schools = result.scalar()

    result = await db.execute(select(func.count()).select_from(Student))
    total_students = result.scalar()

    return {
        "user": {"name": user.full_name, "role": user.role if user.role else ""},
        "total_chapters": total_chapters,
        "total_questions": total_questions,
        "total_assessments": total_assessments,
        "total_results": total_results,
        "total_schools": total_schools,
        "total_students": total_students,
    }
