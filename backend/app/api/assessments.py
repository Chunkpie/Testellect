from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.core.audit import log_audit_entry
from app.models.models import User, Assessment, StudentResult, Student, Blueprint
from app.schemas.assessments import (
    AssessmentCreate,
    AssessmentResponse,
    StudentResultCreate,
    StudentResultResponse,
)

router = APIRouter()


VALID_STATUS_TRANSITIONS = {
    "scheduled": ["conducted"],
    "conducted": ["scored"],
    "scored": ["published"],
}


def _school_scope_filter(model, user):
    if user.role in ("administrator", "deo"):
        return None
    return model.school_id == user.school_id


@router.get("")
async def list_assessments(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("teacher", "principal", "administrator"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )

    stmt = select(Assessment)
    scope = _school_scope_filter(Assessment, current_user)
    if scope is not None:
        stmt = stmt.where(scope)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar()

    stmt = stmt.order_by(Assessment.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    assessments = result.scalars().all()

    return {"items": assessments, "total": total, "limit": limit, "offset": offset}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_assessment(
    data: AssessmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can create assessments",
        )

    bp_result = await db.execute(
        select(Blueprint).where(Blueprint.id == data.blueprint_id)
    )
    if not bp_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Blueprint not found"
        )

    assessment = Assessment(**data.model_dump())
    db.add(assessment)
    await db.commit()
    await db.refresh(assessment)

    await log_audit_entry(
        db=db,
        user_id=current_user.id,
        school_id=assessment.school_id,
        action="create",
        resource_type="assessment",
        resource_id=assessment.id,
    )

    return assessment


@router.patch("/{assessment_id}")
async def update_assessment_status(
    assessment_id: int,
    data: AssessmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can update assessments",
        )

    result = await db.execute(select(Assessment).where(Assessment.id == assessment_id))
    assessment = result.scalar_one_or_none()
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found"
        )

    new_status = data.status
    allowed = VALID_STATUS_TRANSITIONS.get(assessment.status, [])
    if new_status not in allowed and new_status != assessment.status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition from '{assessment.status}' to '{new_status}'. Allowed: {allowed}",
        )

    assessment.status = new_status
    for key, val in data.model_dump(
        exclude={
            "status",
            "school_id",
            "blueprint_id",
            "class_id",
            "name",
            "scheduled_date",
        },
        exclude_unset=True,
    ).items():
        setattr(assessment, key, val)

    await db.commit()
    await db.refresh(assessment)

    await log_audit_entry(
        db=db,
        user_id=current_user.id,
        school_id=assessment.school_id,
        action="update_status",
        resource_type="assessment",
        resource_id=assessment.id,
        extra_data={"new_status": new_status},
    )

    return assessment


@router.get("/{assessment_id}/results")
async def get_assessment_results(
    assessment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("teacher", "principal"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )

    result = await db.execute(select(Assessment).where(Assessment.id == assessment_id))
    assessment = result.scalar_one_or_none()
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found"
        )

    stmt = select(StudentResult).where(StudentResult.assessment_id == assessment_id)
    stmt = stmt.order_by(StudentResult.id)
    result = await db.execute(stmt)
    student_results = result.scalars().all()

    return {"items": student_results, "total": len(student_results)}


class ManualMarksEntry(BaseModel):
    student_marks: list[StudentResultCreate]


@router.post("/{assessment_id}/results/manual", status_code=status.HTTP_201_CREATED)
async def enter_manual_marks(
    assessment_id: int,
    data: ManualMarksEntry,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can enter manual marks",
        )

    result = await db.execute(select(Assessment).where(Assessment.id == assessment_id))
    assessment = result.scalar_one_or_none()
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found"
        )

    created = []
    for item in data.student_marks:
        student_result = StudentResult(
            assessment_id=assessment_id,
            student_id=item.student_id,
            total_score=item.total_score,
            max_score=item.max_score,
            percentage=item.percentage,
        )
        db.add(student_result)
        created.append(student_result)

    await db.commit()
    for sr in created:
        await db.refresh(sr)

    await log_audit_entry(
        db=db,
        user_id=current_user.id,
        school_id=assessment.school_id,
        action="manual_marks_entry",
        resource_type="assessment",
        resource_id=assessment_id,
        extra_data={"count": len(created)},
    )

    return {"items": created, "total": len(created)}
