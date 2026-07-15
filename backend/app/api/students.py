import csv
import io
from fastapi import APIRouter, Depends, HTTPException, Query, status, File, UploadFile
from sqlalchemy.orm import joinedload
from sqlalchemy import select, func, or_, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.core.audit import log_audit_entry
from app.models.models import User, Class, Student, School
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
    grade: int | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("teacher", "principal", "administrator"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    stmt = select(Student).options(joinedload(Student.school), joinedload(Student.class_obj)).where(Student.is_deleted == False)
    scope = _school_scope_filter(Student, current_user)
    if scope is not None:
        stmt = stmt.where(scope)
    if class_id is not None:
        stmt = stmt.where(Student.class_id == class_id)
    if grade is not None:
        stmt = stmt.join(Class, Student.class_id == Class.id).where(Class.grade == grade)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar()

    stmt = stmt.order_by(Student.full_name).offset(offset).limit(limit)
    result = await db.execute(stmt)
    students = result.scalars().all()
    items = [StudentResponse.model_validate(s) for s in students]
    return {"items": items, "total": total, "limit": limit, "offset": offset}


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

    return student


@router.post("/students", status_code=status.HTTP_201_CREATED)
async def create_student(
    data: StudentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("administrator", "deo", "principal", "teacher"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")


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
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("administrator", "deo", "principal", "teacher"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    content = await file.read()
    text = content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))

    schools_result = await db.execute(select(School))
    schools = schools_result.scalars().all()
    school_name_to_id = {s.name.lower(): s.id for s in schools}
    
    classes_result = await db.execute(select(Class))
    classes = classes_result.scalars().all()
    # map (school_id, grade) to class_id
    school_grade_to_class_id = {(c.school_id, c.grade): c.id for c in classes}

    students = []
    errors = []
    
    for row in reader:
        try:
            raw_school = str(row.get("school_id") or row.get("school") or "").strip()
            raw_class = str(row.get("class_id") or row.get("class") or "").strip()

            is_school_scoped = current_user.role in ("teacher", "principal")
            if not row.get("name") or (not is_school_scoped and not raw_school):
                errors.append(f"Row missing required fields (name, school/school_id): {row}")
                continue
            
            # Resolve School
            if is_school_scoped:
                school_id = current_user.school_id
                if raw_school and not raw_school.isdigit():
                    user_school = await db.get(School, school_id)
                    if user_school and user_school.name in ("Model High School", "Adarsh Vidyalaya", "Unity") and user_school.name.lower() != raw_school.lower():
                        user_school.name = raw_school
                        await db.commit()
            else:
                if raw_school.isdigit():
                    school_id = int(raw_school)
                else:
                    school_id = school_name_to_id.get(raw_school.lower())
                    if not school_id:
                        # Auto-create school
                        new_school = School(name=raw_school)
                        db.add(new_school)
                        await db.commit()
                        await db.refresh(new_school)
                        schools.append(new_school)
                        school_name_to_id[raw_school.lower()] = new_school.id
                        school_id = new_school.id

            # Resolve Class
            class_id = None
            if raw_class:
                clean_class = raw_class.lower().replace("th", "").replace("st", "").replace("nd", "").replace("rd", "").strip()
                if clean_class.isdigit():
                    grade = int(clean_class)
                    class_id = school_grade_to_class_id.get((school_id, grade))
                    if not class_id:
                        # Auto-create class
                        new_class = Class(school_id=school_id, grade=grade, academic_year="2026-2027")
                        db.add(new_class)
                        await db.commit()
                        await db.refresh(new_class)
                        school_grade_to_class_id[(school_id, grade)] = new_class.id
                        class_id = new_class.id
                    
            student = Student(
                full_name=row.get("name"),
                roll_number=row.get("roll_number") or None,
                gender=row.get("gender") or None,
                class_id=class_id,
                school_id=school_id,
            )
            students.append(student)
        except Exception as e:
            errors.append(f"Error parsing row {row}: {str(e)}")

    if students:
        db.add_all(students)
        await db.commit()
        for s in students:
            await db.refresh(s)

        await log_audit_entry(
            db=db, user_id=current_user.id, school_id=students[0].school_id,
            action="bulk_import", resource_type="student",
            extra_data={"count": len(students)},
        )

    return {"imported": len(students), "errors": errors}


@router.patch("/students/{student_id}")
async def update_student(
    student_id: int,
    data: StudentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("administrator", "deo", "principal", "teacher"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    result = await db.execute(
        select(Student).where(Student.id == student_id, Student.is_deleted == False)
    )
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    if current_user.role in ("principal", "teacher") and student.school_id != current_user.school_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

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
    if current_user.role not in ("administrator", "deo", "principal", "teacher"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    result = await db.execute(
        select(Student).where(Student.id == student_id, Student.is_deleted == False)
    )
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    if current_user.role in ("principal", "teacher") and student.school_id != current_user.school_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    student.is_deleted = True
    await db.commit()

    await log_audit_entry(
        db=db, user_id=current_user.id, school_id=student.school_id,
        action="delete", resource_type="student", resource_id=student_id,
    )
