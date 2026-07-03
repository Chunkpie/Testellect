from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.core.audit import log_audit_entry
from app.models.models import User, Subject
from app.schemas.curriculum import SubjectCreate, SubjectResponse

router = APIRouter()


@router.get("")
async def list_subjects(
    grade: int | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Subject)
    if grade is not None:
        stmt = stmt.where(Subject.grade == grade)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar()

    stmt = stmt.order_by(Subject.grade, Subject.name_en).offset(offset).limit(limit)
    result = await db.execute(stmt)
    subjects = result.scalars().all()

    return {"items": subjects, "total": total, "limit": limit, "offset": offset}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_subject(
    data: SubjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "administrator":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only administrators can create subjects")

    subject = Subject(**data.model_dump())
    db.add(subject)
    await db.commit()
    await db.refresh(subject)

    await log_audit_entry(
        db=db, user_id=current_user.id, school_id=current_user.school_id,
        action="create", resource_type="subject", resource_id=subject.id,
    )

    return subject
