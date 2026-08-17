from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone

from app.core.deps import get_db, get_current_user
from app.models.models import User, School, Student, Teacher
from app.models.models import Assessment, StudentResult
from app.models.models import QuestionBank, Blueprint, Subject
from app.models.models import Report

router = APIRouter()


def _school_scope(user: User):
    if user.role not in ("admin", "deo"):
        return user.school_id
    return None


@router.get("/stats")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    scope = _school_scope(user)

    q = select(func.count()).select_from(Student).where(Student.is_deleted == False)
    if scope:
        q = q.where(Student.school_id == scope)
    result = await db.execute(q)
    total_students = result.scalar()

    q = select(func.count()).select_from(Teacher)
    if scope:
        q = q.where(Teacher.school_id == scope)
    result = await db.execute(q)
    total_teachers = result.scalar()

    q = select(func.count()).select_from(Assessment)
    if scope:
        q = q.where(Assessment.school_id == scope)
    result = await db.execute(q)
    total_assessments = result.scalar()

    q = (
        select(func.count())
        .select_from(QuestionBank)
        .where(QuestionBank.is_deleted == False)
    )
    if scope:
        q = q.where(QuestionBank.school_id == scope)
    result = await db.execute(q)
    total_questions = result.scalar()

    score_q = select(func.avg(StudentResult.percentage))
    if scope:
        score_q = score_q.join(
            Assessment, StudentResult.assessment_id == Assessment.id
        ).where(Assessment.school_id == scope)
    result = await db.execute(score_q)
    avg_score = result.scalar()
    average_score = round(float(avg_score), 2) if avg_score else 0.0

    completed_q = select(func.count(func.distinct(StudentResult.student_id)))
    if scope:
        completed_q = completed_q.join(
            Assessment, StudentResult.assessment_id == Assessment.id
        ).where(Assessment.school_id == scope)
    result = await db.execute(completed_q)
    students_with_results = result.scalar()

    completion_rate = (
        round((students_with_results / total_students) * 100, 2)
        if total_students > 0
        else 0.0
    )

    return {
        "total_students": total_students,
        "total_teachers": total_teachers,
        "total_assessments": total_assessments,
        "total_questions": total_questions,
        "average_score": average_score,
        "completion_rate": completion_rate,
    }


@router.get("/subject-performance")
async def get_subject_performance(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    scope = _school_scope(user)

    q = (
        select(
            Subject.id,
            Subject.name_en,
            func.avg(StudentResult.percentage).label("avg_score"),
            func.count(func.distinct(StudentResult.student_id)).label("student_count"),
        )
        .join(Assessment, StudentResult.assessment_id == Assessment.id)
        .join(Blueprint, Assessment.blueprint_id == Blueprint.id)
        .join(Subject, Blueprint.subject_id == Subject.id)
    )
    if scope:
        q = q.where(Assessment.school_id == scope)
    q = q.group_by(Subject.id, Subject.name_en).order_by(Subject.name_en)

    result = await db.execute(q)
    rows = result.all()

    return [
        {
            "subject_id": row.id,
            "subject_name": row.name_en,
            "average_score": round(float(row.avg_score), 2) if row.avg_score else 0.0,
            "student_count": row.student_count,
        }
        for row in rows
    ]


@router.get("/bloom-distribution")
async def get_bloom_distribution(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    scope = _school_scope(user)

    q = select(
        QuestionBank.bloom_level,
        func.count().label("count"),
    ).where(QuestionBank.is_deleted == False)
    if scope:
        q = q.where(QuestionBank.school_id == scope)
    q = q.group_by(QuestionBank.bloom_level)

    result = await db.execute(q)
    rows = result.all()

    total = sum(r.count for r in rows) or 1

    return [
        {
            "level": r.bloom_level,
            "count": r.count,
            "percentage": round((r.count / total) * 100, 1),
        }
        for r in rows
    ]


@router.get("/score-trends")
async def get_score_trends(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cutoff = datetime.now(timezone.utc).date() - timedelta(days=days)
    scope = _school_scope(user)

    q = (
        select(
            Assessment.scheduled_date,
            func.avg(StudentResult.percentage).label("score"),
            func.count(func.distinct(StudentResult.id)).label("assessment_count"),
        )
        .join(Assessment, StudentResult.assessment_id == Assessment.id)
        .where(Assessment.scheduled_date >= cutoff)
    )
    if scope:
        q = q.where(Assessment.school_id == scope)
    q = q.group_by(Assessment.scheduled_date).order_by(Assessment.scheduled_date)

    result = await db.execute(q)
    rows = result.all()

    return [
        {
            "date": r.scheduled_date.isoformat() if r.scheduled_date else None,
            "score": round(float(r.score), 2) if r.score else 0.0,
            "assessment_count": r.assessment_count,
        }
        for r in rows
    ]


@router.get("")
async def list_reports(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = select(Report).order_by(Report.generated_at.desc().nullslast())
    if user.role not in ("admin", "deo"):
        q = q.where(Report.school_id == user.school_id)

    result = await db.execute(q)
    reports = result.scalars().all()

    return {
        "items": [
            {
                "id": r.id,
                "title": (
                    f"{r.report_type.replace('_', ' ').title()} Report"
                    if r.report_type
                    else "Report"
                ),
                "report_type": r.report_type or "unknown",
                "school_id": r.school_id,
                "generated_at": r.generated_at.isoformat() if r.generated_at else None,
                "parameters": "{}",
            }
            for r in reports
        ],
        "total": len(reports),
    }


@router.post("/generate")
async def generate_report(
    report_type: str = Query(
        ...,
        description="Report type: school_summary, class_performance, student_detail",
    ),
    school_id: int = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    target_school = school_id or user.school_id
    if not target_school:
        raise HTTPException(status_code=400, detail="School ID is required")

    report = Report(
        school_id=target_school,
        report_type=report_type,
        generated_at=datetime.now(timezone.utc),
        generated_by=user.id,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    return {
        "id": report.id,
        "title": f"{report_type.replace('_', ' ').title()} Report",
        "report_type": report.report_type,
        "school_id": report.school_id,
        "generated_at": (
            report.generated_at.isoformat() if report.generated_at else None
        ),
        "parameters": "{}",
    }


@router.get("/{report_id}")
async def get_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return {
        "id": report.id,
        "title": (
            f"{report.report_type.replace('_', ' ').title()} Report"
            if report.report_type
            else "Report"
        ),
        "report_type": report.report_type,
        "school_id": report.school_id,
        "generated_at": (
            report.generated_at.isoformat() if report.generated_at else None
        ),
        "parameters": "{}",
    }


@router.get("/{report_id}/download")
async def download_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    from app.services.pdf_report_service import PDFReportService
    from fastapi.responses import FileResponse

    if report.report_type == "school_summary":
        filepath = await PDFReportService.generate_school_summary(
            db, report.school_id, report.id
        )
    else:
        # Default to a generic report or student report
        filepath = await PDFReportService.generate_school_summary(
            db, report.school_id, report.id
        )

    return FileResponse(
        filepath,
        media_type="application/pdf",
        filename=f"report_{report.id}.pdf",
    )


@router.delete("/{report_id}")
async def delete_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    await db.delete(report)
    await db.commit()
    return {"message": "Report deleted"}
