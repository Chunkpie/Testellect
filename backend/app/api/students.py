from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, or_, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.core.audit import log_audit_entry
from app.models.models import User, Class, Student
from app.schemas.students import ClassCreate, ClassResponse, StudentCreate, StudentResponse, StudentUpdate

router = APIRouter()


def _school_scope_filter(model, user):
    if user.role in ("administrator", "deo"):
        return None
    return model.school_id == user.school_id


# ---- Classes ----

@router.get("/classes")
async def list_classes(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("teacher", "principal", "administrator"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    stmt = select(Class)
    scope = _school_scope_filter(Class, current_user)
    if scope is not None:
        stmt = stmt.where(scope)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar()

    stmt = stmt.order_by(Class.grade, Class.section).offset(offset).limit(limit)
    result = await db.execute(stmt)
    classes = result.scalars().all()

    return {"items": classes, "total": total, "limit": limit, "offset": offset}


@router.post("/classes", status_code=status.HTTP_201_CREATED)
async def create_class(
    data: ClassCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "administrator":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only administrators can create classes")

    cls = Class(**data.model_dump())
    db.add(cls)
    await db.commit()
    await db.refresh(cls)

    await log_audit_entry(
        db=db, user_id=current_user.id, school_id=cls.school_id,
        action="create", resource_type="class", resource_id=cls.id,
    )

    return cls


@router.patch("/classes/{class_id}")
async def update_class(
    class_id: int,
    data: ClassCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "administrator":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only administrators can update classes")

    result = await db.execute(select(Class).where(Class.id == class_id))
    cls = result.scalar_one_or_none()
    if not cls:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found")

    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(cls, key, val)

    await db.commit()
    await db.refresh(cls)

    await log_audit_entry(
        db=db, user_id=current_user.id, school_id=cls.school_id,
        action="update", resource_type="class", resource_id=cls.id,
    )

    return cls


@router.delete("/classes/{class_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_class(
    class_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "administrator":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only administrators can delete classes")

    result = await db.execute(select(Class).where(Class.id == class_id))
    cls = result.scalar_one_or_none()
    if not cls:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found")

    await db.delete(cls)
    await db.commit()

    await log_audit_entry(
        db=db, user_id=current_user.id, school_id=cls.school_id,
        action="delete", resource_type="class", resource_id=class_id,
    )


# ---- Students ----

@router.get("/students")
async def list_students(
    class_id: int | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("teacher", "principal", "administrator"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    stmt = select(Student).where(Student.is_deleted == False)
    scope = _school_scope_filter(Student, current_user)
    if scope is not None:
        stmt = stmt.where(scope)
    if class_id is not None:
        stmt = stmt.where(Student.class_id == class_id)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar()

    stmt = stmt.order_by(Student.full_name).offset(offset).limit(limit)
    result = await db.execute(stmt)
    students = result.scalars().all()

    return {"items": students, "total": total, "limit": limit, "offset": offset}


@router.get("/students/{student_id}")
async def get_student(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("teacher", "principal", "administrator"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    result = await db.execute(
        select(Student).where(Student.id == student_id, Student.is_deleted == False)
    )
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    scope = _school_scope_filter(Student, current_user)
    if scope is not None and not (student.school_id == current_user.school_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return student


@router.post("/students", status_code=status.HTTP_201_CREATED)
async def create_student(
    data: StudentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "administrator":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only administrators can create students")

    student = Student(**data.model_dump())
    db.add(student)
    await db.commit()
    await db.refresh(student)

    await log_audit_entry(
        db=db, user_id=current_user.id, school_id=student.school_id,
        action="create", resource_type="student", resource_id=student.id,
    )

    return student


@router.post("/students/bulk-import", status_code=status.HTTP_201_CREATED)
async def bulk_import_students(
    data: list[StudentCreate],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "administrator":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only administrators can bulk import students")

    students = [Student(**item.model_dump()) for item in data]
    db.add_all(students)
    await db.commit()
    for s in students:
        await db.refresh(s)

    await log_audit_entry(
        db=db, user_id=current_user.id, school_id=students[0].school_id if students else None,
        action="bulk_import", resource_type="student",
        extra_data={"count": len(students)},
    )

    return {"items": students, "total": len(students)}


@router.patch("/students/{student_id}")
async def update_student(
    student_id: int,
    data: StudentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "administrator":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only administrators can update students")

    result = await db.execute(
        select(Student).where(Student.id == student_id, Student.is_deleted == False)
    )
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(student, key, val)

    await db.commit()
    await db.refresh(student)

    await log_audit_entry(
        db=db, user_id=current_user.id, school_id=student.school_id,
        action="update", resource_type="student", resource_id=student.id,
    )

    return student


@router.delete("/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_student(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "administrator":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only administrators can delete students")

    result = await db.execute(
        select(Student).where(Student.id == student_id, Student.is_deleted == False)
    )
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    student.is_deleted = True
    await db.commit()

    await log_audit_entry(
        db=db, user_id=current_user.id, school_id=student.school_id,
        action="delete", resource_type="student", resource_id=student_id,
    )
