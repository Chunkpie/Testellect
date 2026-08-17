from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import pandas as pd
import tempfile
import os

from app.core.deps import get_db, get_current_user
from app.db.models.auth import User
from app.db.models.assessments import Student, StudentResult, Assessment

router = APIRouter()


@router.get("/students")
async def export_students(
    school_id: int | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    target_school = school_id or user.school_id
    if not target_school:
        raise HTTPException(status_code=400, detail="School ID required")

    stmt = select(Student).where(
        Student.school_id == target_school, Student.is_deleted == False
    )
    result = await db.execute(stmt)
    students = result.scalars().all()

    data = []
    for s in students:
        data.append(
            {
                "ID": s.id,
                "Name": s.full_name,
                "Roll Number": s.roll_number,
                "GR Number": s.gr_number,
                "Gender": s.gender,
                "Class ID": s.class_id,
            }
        )

    df = pd.DataFrame(data)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        df.to_excel(tmp.name, index=False)
        tmp_path = tmp.name

    return FileResponse(
        tmp_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f"students_export_school_{target_school}.xlsx",
    )


@router.get("/assessments/{assessment_id}/results")
async def export_assessment_results(
    assessment_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    assessment = await db.get(Assessment, assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    stmt = (
        select(StudentResult, Student)
        .join(Student)
        .where(StudentResult.assessment_id == assessment_id)
    )
    result = await db.execute(stmt)
    rows = result.all()

    data = []
    for sr, student in rows:
        data.append(
            {
                "Student ID": student.id,
                "Student Name": student.full_name,
                "Roll Number": student.roll_number,
                "Total Score": sr.total_score,
                "Max Score": sr.max_score,
                "Percentage": (
                    f"{sr.percentage}%" if sr.percentage is not None else "N/A"
                ),
            }
        )

    df = pd.DataFrame(data)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
        df.to_csv(tmp.name, index=False)
        tmp_path = tmp.name

    return FileResponse(
        tmp_path,
        media_type="text/csv",
        filename=f"results_assessment_{assessment_id}.csv",
    )
