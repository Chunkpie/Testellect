from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from app.core.deps import get_db, get_current_user
from app.db.models.auth import User, School
from app.db.models.assessments import Student, Assessment, StudentResult, CompetencyResult
from app.db.models.omr import OMRSheet, OMRResult
from app.db.models.questions import QuestionBank
import json
from app.services.learning_analytics_service import LearningAnalyticsService

router = APIRouter()

@router.get("/district/{district}")
async def district_analytics(district: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(School).where(School.district == district))
    schools = result.scalars().all()
    school_ids = [s.id for s in schools]

    total_students = 0
    if school_ids:
        result = await db.execute(
            select(func.count()).select_from(Student).where(Student.school_id.in_(school_ids))
        )
        total_students = result.scalar()

    assessments = []
    assessment_ids = []
    if school_ids:
        result = await db.execute(select(Assessment).where(Assessment.school_id.in_(school_ids)))
        assessments = result.scalars().all()
        assessment_ids = [a.id for a in assessments]

    results = []
    if assessment_ids:
        result = await db.execute(select(StudentResult).where(StudentResult.assessment_id.in_(assessment_ids)))
        results = result.scalars().all()

    scores = [r.percentage for r in results if r.percentage is not None]
    return {
        "district": district,
        "total_schools": len(schools),
        "total_students": total_students,
        "total_assessments": len(assessments),
        "total_results": len(results),
        "average_score": round(sum(scores) / len(scores), 2) if scores else 0,
    }


@router.get("/school/{school_id}")
async def school_analytics(school_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(func.count()).select_from(Student).where(Student.school_id == school_id)
    )
    student_count = result.scalar()

    result = await db.execute(select(Assessment).where(Assessment.school_id == school_id))
    assessments = result.scalars().all()
    assessment_ids = [a.id for a in assessments]

    results = []
    if assessment_ids:
        result = await db.execute(select(StudentResult).where(StudentResult.assessment_id.in_(assessment_ids)))
        results = result.scalars().all()

    scores = [r.percentage for r in results if r.percentage is not None]
    return {
        "school_id": school_id,
        "total_students": student_count,
        "total_assessments": len(assessments),
        "total_results": len(results),
        "average_score": round(sum(scores) / len(scores), 2) if scores else 0,
    }


@router.get("/assessment/{assessment_id}")
async def assessment_analytics(assessment_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Assessment).where(Assessment.id == assessment_id))
    assessment = result.scalar_one_or_none()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    result = await db.execute(select(StudentResult).where(StudentResult.assessment_id == assessment_id))
    results = result.scalars().all()

    scores = [r.percentage for r in results if r.percentage is not None]

    # Aggregate competencies
    competency_aggregate = {}
    if results:
        res_ids = [r.id for r in results]
        comp_res = await db.execute(select(CompetencyResult).where(CompetencyResult.student_result_id.in_(res_ids)))
        c_results = comp_res.scalars().all()
        for cr in c_results:
            if cr.competency_id not in competency_aggregate:
                competency_aggregate[cr.competency_id] = {"attempted": 0, "correct": 0}
            competency_aggregate[cr.competency_id]["attempted"] += cr.questions_attempted or 0
            competency_aggregate[cr.competency_id]["correct"] += cr.questions_correct or 0

    comp_averages = {}
    for cid, data in competency_aggregate.items():
        if data["attempted"] > 0:
            comp_averages[cid] = round((data["correct"] / data["attempted"]) * 100, 2)

    return {
        "assessment_id": assessment_id,
        "total_results": len(results),
        "average_score": round(sum(scores) / len(scores), 2) if scores else 0,
        "max_score": max(scores) if scores else 0,
        "min_score": min(scores) if scores else 0,
        "competency_averages": comp_averages,
    }


@router.get("/student/{student_id}")
async def student_analytics(student_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(StudentResult).where(StudentResult.student_id == student_id))
    results = result.scalars().all()
    
    analytics_svc = LearningAnalyticsService()
    insights = await analytics_svc.generate_student_insights(db, student_id)

    return {
        "student_id": student_id,
        "total_assessments": len(results),
        "results": [{"id": r.id, "score": r.total_score, "percentage": r.percentage, "max_score": r.max_score} for r in results],
        "insights": insights
    }

@router.get("/competencies")
async def get_competency_radar(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Fetch all OMR results that belong to the user's scope
    # For simplicity, we fetch all for now, or filter by user's school
    stmt = select(OMRResult).join(OMRSheet).where(OMRSheet.assessment_id.is_not(None))
    if user.school_id:
        stmt = stmt.join(Assessment, OMRSheet.assessment_id == Assessment.id).where(Assessment.school_id == user.school_id)
        
    result = await db.execute(stmt)
    omr_results = result.scalars().all()
    
    # Extract all question IDs answered and whether they were correct
    question_stats = {}
    for r in omr_results:
        if not r.detected_answers:
            continue
        try:
            answers = json.loads(r.detected_answers)
            for ans in answers:
                qid = ans.get("question_id")
                if not qid:
                    continue
                if qid not in question_stats:
                    question_stats[qid] = {"attempted": 0, "correct": 0}
                question_stats[qid]["attempted"] += 1
                if ans.get("is_correct"):
                    question_stats[qid]["correct"] += 1
        except:
            continue
            
    if not question_stats:
        return []
        
    # Lookup bloom levels for these questions
    q_stmt = select(QuestionBank.id, QuestionBank.bloom_level).where(QuestionBank.id.in_(list(question_stats.keys())))
    q_res = await db.execute(q_stmt)
    
    bloom_agg = {}
    for qid, bloom in q_res.all():
        b = bloom or "Knowledge"
        b = b.capitalize()
        if b not in bloom_agg:
            bloom_agg[b] = {"attempted": 0, "correct": 0}
        bloom_agg[b]["attempted"] += question_stats[qid]["attempted"]
        bloom_agg[b]["correct"] += question_stats[qid]["correct"]
        
    # Format for RadarChart
    radar_data = []
    for bloom, stats in bloom_agg.items():
        perc = round((stats["correct"] / stats["attempted"]) * 100) if stats["attempted"] > 0 else 0
        radar_data.append({
            "subject": bloom,
            "A": perc,
            "fullMark": 100
        })
        
    # Default data if nothing found
    if not radar_data:
        radar_data = [
            {"subject": "Knowledge", "A": 0, "fullMark": 100},
            {"subject": "Understanding", "A": 0, "fullMark": 100},
            {"subject": "Application", "A": 0, "fullMark": 100},
            {"subject": "Analysis", "A": 0, "fullMark": 100},
        ]
        
    return radar_data
