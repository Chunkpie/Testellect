from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.core.audit import log_audit_entry
from app.models.models import User, School, Class
from app.schemas.schools import SchoolCreate, SchoolResponse, SchoolUpdate

router = APIRouter()


@router.get("")
async def list_schools(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("administrator", "deo"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    stmt = select(School)
    if current_user.role == "administrator" and current_user.school_id:
        stmt = stmt.where(School.id == current_user.school_id)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar()

    stmt = stmt.order_by(School.name).offset(offset).limit(limit)
    result = await db.execute(stmt)
    schools = result.scalars().all()

    return {"items": schools, "total": total, "limit": limit, "offset": offset}


@router.get("/{school_id}")
async def get_school(
    school_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("administrator", "deo", "principal"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    result = await db.execute(select(School).where(School.id == school_id))
    school = result.scalar_one_or_none()
    if not school:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="School not found")

    if current_user.role == "principal" and current_user.school_id != school.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return school


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_school(
    data: SchoolCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "deo":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only DEO can create schools")

    school = School(**data.model_dump())
    db.add(school)
    await db.commit()
    await db.refresh(school)

    await log_audit_entry(
        db=db,
        user_id=current_user.id,
        school_id=school.id,
        action="create",
        resource_type="school",
        resource_id=school.id,
    )
    # Auto-create grades 1-12 for the new school
    from datetime import datetime
    current_year = datetime.now().year
    academic_year = f"{current_year}-{str(current_year + 1)[-2:]}"
    for grade in range(1, 13):
        db.add(Class(school_id=school.id, grade=grade, section="A", academic_year=academic_year))
    await db.commit()

    return school


@router.patch("/{school_id}")
async def update_school(
    school_id: int,
    data: SchoolUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("administrator", "deo"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    result = await db.execute(select(School).where(School.id == school_id))
    school = result.scalar_one_or_none()
    if not school:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="School not found")

    if current_user.role == "administrator" and current_user.school_id != school.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Can only update own school")

    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(school, key, val)

    await db.commit()
    await db.refresh(school)

    await log_audit_entry(
        db=db,
        user_id=current_user.id,
        school_id=school.id,
        action="update",
        resource_type="school",
        resource_id=school.id,
        extra_data={"updated_fields": list(data.model_dump(exclude_unset=True).keys())},
    )

    return school
