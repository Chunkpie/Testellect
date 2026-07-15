import json
import os
import time
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import func, select, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit_entry
from app.core.deps import get_current_user, get_db
from app.db.models.assessments import Assessment, StudentResult, CompetencyResult, Student
from app.db.models.auth import User
from app.db.models.omr import OMRResult, OMRSheet
from app.db.models.papers import Paper, PaperQuestion, Blueprint
from app.db.models.questions import QuestionOption, QuestionBank
from app.db.models.curriculum import Competency
from app.services.omr_service import generate_omr_pdf
from app.services.omr_cv_service import OMRCVService
from app.services.learning_analytics_service import LearningAnalyticsService
from app.services.pdf_report_service import PDFReportService
from fastapi.responses import FileResponse, StreamingResponse
import tempfile
import shutil
import zipfile
import io

router = APIRouter()


@router.get("")
async def list_omr_sessions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(OMRSheet.batch_id, OMRSheet.paper_id, func.min(OMRSheet.created_at).label("created_at"), func.count(OMRSheet.id).label("sheet_count"))
        .where(OMRSheet.batch_id.is_not(None))
        .group_by(OMRSheet.batch_id, OMRSheet.paper_id)
        .order_by(func.min(OMRSheet.created_at).desc())
    )
    result = await db.execute(stmt)
    rows = result.all()

    items = []
    for batch_id, paper_id, created_at, sheet_count in rows:
        paper = await db.get(Paper, paper_id)
        bp = await db.get(Blueprint, paper.blueprint_id) if paper else None

        # Count results
        sheets_sub = select(OMRSheet.id).where(OMRSheet.batch_id == batch_id).subquery()
        res_count = await db.scalar(
            select(func.count(OMRResult.id)).where(OMRResult.omr_sheet_id.in_(select(sheets_sub.c.id)))
        )

        items.append({
            "batch_id": batch_id,
            "paper_id": paper_id,
            "paper_name": paper.variant_label if paper else "Unknown",
            "grade": bp.grade if bp else 0,
            "subject_id": bp.subject_id if bp else 0,
            "student_count": sheet_count,
            "created_at": created_at.isoformat() if created_at else None,
            "has_results": (res_count or 0) > 0,
        })

    return {"items": items, "total": len(items)}


def _compute_session_id() -> str:
    return f"SESSION_{int(time.time() * 1000)}"


class GenerateOMRRequest(BaseModel):
    paper_id: int
    class_id: int
    total_questions: int | None = None


@router.post("/generate")
async def generate_omr(
    req: GenerateOMRRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    paper_id = req.paper_id
    class_id = req.class_id
    total_questions = req.total_questions

    paper = await db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found")

    blueprint = await db.get(Blueprint, paper.blueprint_id)
    if not blueprint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blueprint not found")

    # Fetch students in the selected class
    students_stmt = select(Student).where(
        Student.class_id == class_id, 
        Student.is_active == True, 
        Student.is_deleted == False
    )
    students = (await db.execute(students_stmt)).scalars().all()

    if not students:
        raise HTTPException(status_code=400, detail="No active students found in this class.")

    batch_id = _compute_session_id()

    # Find or create an assessment for this blueprint and class
    stmt = select(Assessment).where(
        Assessment.blueprint_id == paper.blueprint_id,
        Assessment.class_id == class_id,
        Assessment.school_id == user.school_id,
    ).order_by(Assessment.created_at.desc()).limit(1)
    result = await db.execute(stmt)
    assessment = result.scalar_one_or_none()

    if not assessment:
        assessment = Assessment(
            school_id=user.school_id or blueprint.school_id,
            blueprint_id=paper.blueprint_id,
            class_id=class_id,
            name=f"OMR - {blueprint.name}",
            status="scheduled",
        )
        db.add(assessment)
        await db.flush()

    # Find all variants (papers) for this blueprint
    papers_stmt = select(Paper).where(Paper.blueprint_id == paper.blueprint_id)
    all_variants = (await db.execute(papers_stmt)).scalars().all()

    sheets_created = []
    # Create OMRSheet records for each student and each variant
    for variant in all_variants:
        for student in students:
            sheet = OMRSheet(
                paper_id=variant.id,
                assessment_id=assessment.id,
                student_id=student.id,
                qr_payload=batch_id, # Replaced later in PDF gen if needed, but DB stores batch_id for legacy
                sheet_pdf_path=None,
                status="generated",
                batch_id=batch_id,
            )
            db.add(sheet)
            await db.flush()
            sheets_created.append({"id": sheet.id, "paper_name": variant.variant_label, "student_name": student.full_name})

    await db.commit()

    await log_audit_entry(
        db, user_id=user.id,
        action="CREATE_OMR_SESSION",
        resource_type="omr",
        extra_data={"batch_id": batch_id, "paper_id": paper_id, "class_id": class_id, "student_count": len(students)}
    )

    total_q = total_questions if total_questions and total_questions > 0 else blueprint.total_questions

    from app.services.omr_service import generate_omr_pdf
    pdf_path = generate_omr_pdf(
        paper_id=paper_id,
        students=students,
        school_id=user.school_id or blueprint.school_id,
        paper_name=paper.variant_label,
        total_questions=total_q,
        batch_id=batch_id,
    )

    from sqlalchemy import update
    await db.execute(
        update(OMRSheet).where(OMRSheet.batch_id == batch_id).values(sheet_pdf_path=pdf_path)
    )
    await db.commit()

    return {
        "batch_id": batch_id,
        "paper_id": paper_id,
        "paper_name": blueprint.name,
        "student_count": 0,
        "file_path": pdf_path,
        "sheets_created": sheets_created,
    }


@router.get("/{batch_id}")
async def get_omr_session(
    batch_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(OMRSheet).where(OMRSheet.batch_id == batch_id).order_by(OMRSheet.id)
    result = await db.execute(stmt)
    sheets = result.scalars().all()

    if not sheets:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    first = sheets[0]
    paper = await db.get(Paper, first.paper_id)
    bp = await db.get(Blueprint, paper.blueprint_id) if paper else None

    from app.db.models.assessments import Student
    sheet_list = []
    for s in sheets:
        student_name = "Unknown"
        if s.student_id:
            st = await db.get(Student, s.student_id)
            if st:
                student_name = st.full_name

        sheet_list.append({
            "id": s.id,
            "student_id": s.student_id,
            "student_name": student_name,
            "status": s.status,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        })

    return {
        "batch_id": batch_id,
        "paper_id": first.paper_id,
        "paper_name": paper.variant_label if paper else "Unknown",
        "grade": bp.grade if bp else 0,
        "subject_id": bp.subject_id if bp else 0,
        "total_questions": bp.total_questions if bp else 0,
        "student_count": len(sheets),
        "status": first.status,
        "created_at": first.created_at.isoformat() if first.created_at else None,
        "sheets": sheet_list,
    }


@router.get("/{batch_id}/download")
async def download_omr_pdf(
    batch_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(OMRSheet).where(OMRSheet.batch_id == batch_id).limit(1)
    result = await db.execute(stmt)
    sheet = result.scalar_one_or_none()

    if not sheet or not sheet.sheet_pdf_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDF not found")

    filepath = sheet.sheet_pdf_path
    if not os.path.isfile(filepath):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found on disk")

    paper = await db.get(Paper, sheet.paper_id)
    filename = f"omr_{paper.variant_label.replace(' ', '_') if paper else batch_id}.pdf"

    return FileResponse(filepath, media_type="application/pdf", filename=filename)


@router.post("/{batch_id}/results")
async def submit_omr_results(
    batch_id: str,
    answers: list[dict] = ...,  # JSON body: [{question_id: int, answer: str}]
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not isinstance(answers, list):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Expected a JSON array of answers")

    stmt = select(OMRSheet).where(OMRSheet.batch_id == batch_id)
    result = await db.execute(stmt)
    sheets = result.scalars().all()

    if not sheets:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    first = sheets[0]
    paper = await db.get(Paper, first.paper_id)
    if not paper:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found")

    bp = await db.get(Blueprint, paper.blueprint_id)
    max_score = float(bp.total_questions) if bp else float(len(answers))
    
    # Delegate to helper
    eval_result = None
    for sheet in sheets:
        eval_result = await _evaluate_and_save_result(db, sheet, answers, user.id, max_score)

    await db.commit()

    await log_audit_entry(
        db=db,
        user_id=user.id,
        school_id=user.school_id,
        action="submit_omr_results",
        resource_type="omr_result",
        extra_data={"batch_id": batch_id, "score": eval_result["summary"]["correct"] if eval_result else 0, "max_score": max_score},
    )

    return eval_result or {
        "evaluated": [],
        "summary": {"correct": 0, "total": max_score, "percentage": 0}
    }

async def _evaluate_and_save_result(db: AsyncSession, sheet: OMRSheet, answers: list[dict], user_id: int, max_score: float) -> dict:
    correct_count = 0

    # Resolve correct answers from the question bank
    pq_stmt = (
        select(PaperQuestion)
        .where(PaperQuestion.paper_id == sheet.paper_id)
        .order_by(PaperQuestion.sequence)
    )
    result = await db.execute(pq_stmt)
    paper_questions = result.scalars().all()

    correct_answers: dict[int, dict] = {}
    answer_key: dict[int, str] = {}
    for pq in paper_questions:
        qb = await db.get(QuestionBank, pq.question_id)
        competency_id = qb.competency_id if (qb and qb.competency_id) else 9999

        q_opts_stmt = (
            select(QuestionOption)
            .where(QuestionOption.question_id == pq.question_id)
            .order_by(QuestionOption.sequence)
        )
        result = await db.execute(q_opts_stmt)
        options = result.scalars().all()

        # Map option_order (e.g., "BCAD") to A/B/C/D letters
        order = pq.option_order or "ABCD"
        correct_letter = None
        for idx, opt in enumerate(options):
            if opt.is_correct and idx < len(order):
                correct_letter = order[idx]
                break
        # Fallback: find is_correct directly by sequence
        if correct_letter is None:
            for idx, opt in enumerate(options):
                if opt.is_correct:
                    correct_letter = chr(65 + idx)
                    break

        question_key = pq.sequence or pq.question_id
        correct_answers[question_key] = {
            "question_id": pq.question_id,
            "competency_id": competency_id,
            "sequence": pq.sequence,
            "correct_answer": correct_letter or "",
            "options": [{"text": o.option_text_en, "letter": order[i] if i < len(order) else chr(65 + i)}
                        for i, o in enumerate(options)],
        }
        answer_key[question_key] = correct_letter or ""

    # Evaluate answers
    evaluated_answers = []
    
    # Pre-populate all questions as unanswered
    for k, v in correct_answers.items():
        evaluated_answers.append({
            "question_id": v["question_id"],
            "sequence": v["sequence"],
            "student_answer": "",
            "correct_answer": v["correct_answer"],
            "is_correct": False,
            "competency_id": v.get("competency_id"),
        })

    import logging
    logging.info(f"RECEIVED ANSWERS: {answers}")
    for ans in answers:
        qid = ans.get("question_id")
        student_ans = ans.get("answer", "").strip().upper()
        
        for ea in evaluated_answers:
            # The 'question_id' from the frontend/CV service is actually the sequence number (1, 2, 3)
            # So we match against ea["sequence"] or ea["question_id"]
            if str(ea.get("sequence", "")) == str(qid) or str(ea.get("question_id", "")) == str(qid):
                ea["student_answer"] = student_ans
                ea["is_correct"] = student_ans == ea["correct_answer"]
                if ea["is_correct"]:
                    correct_count += 1
                break

    score = correct_count
    percentage = round((score / max_score * 100), 2) if max_score > 0 else 0

    # Create OMRResult records for the sheet
    stmt = select(OMRResult).where(OMRResult.omr_sheet_id == sheet.id)
    res = await db.execute(stmt)
    existing = res.scalar_one_or_none()
    if not existing:
        omr_result = OMRResult(
            omr_sheet_id=sheet.id,
            detected_answers=json.dumps(evaluated_answers),
            raw_score=float(score),
            max_score=float(max_score),
            scan_confidence=100.0,
            scanned_by=user_id,
            scanned_at=datetime.utcnow(),
        )
        db.add(omr_result)
        await db.flush()
    else:
        existing.detected_answers = json.dumps(evaluated_answers)
        existing.raw_score = float(score)
        existing.max_score = float(max_score)
        existing.scanned_by = user_id
        existing.scanned_at = datetime.utcnow()
        omr_result = existing

    # Create StudentResult only if student is assigned
    if sheet.student_id is not None:
        sr_stmt = select(StudentResult).where(
            StudentResult.assessment_id == sheet.assessment_id,
            StudentResult.student_id == sheet.student_id
        )
        sr_res = await db.execute(sr_stmt)
        student_result = sr_res.scalar_one_or_none()

        if not student_result:
            student_result = StudentResult(
                assessment_id=sheet.assessment_id,
                student_id=sheet.student_id,
                omr_result_id=omr_result.id,
                total_score=float(score),
                max_score=float(max_score),
                percentage=percentage
            )
            db.add(student_result)
        else:
            student_result.omr_result_id = omr_result.id
            student_result.total_score = float(score)
            student_result.max_score = float(max_score)
            student_result.percentage = percentage

        await db.flush()

        # Aggregate and save CompetencyResult
        competency_stats = {}
        for ev in evaluated_answers:
            cid = ev.get("competency_id")
            if cid:
                if cid not in competency_stats:
                    competency_stats[cid] = {"attempted": 0, "correct": 0}
                if ev.get("student_answer"):
                    competency_stats[cid]["attempted"] += 1
                if ev.get("is_correct"):
                    competency_stats[cid]["correct"] += 1

        # Clear existing competency results
        await db.execute(sa_delete(CompetencyResult).where(CompetencyResult.student_result_id == student_result.id))

        for cid, stats in competency_stats.items():
            cr = CompetencyResult(
                student_result_id=student_result.id,
                competency_id=cid,
                questions_attempted=stats["attempted"],
                questions_correct=stats["correct"]
            )
            db.add(cr)

    sheet.status = "evaluated"
        
    return {
        "batch_id": sheet.batch_id,
        "evaluated": evaluated_answers,
        "summary": {
            "correct": correct_count,
            "total": max_score,
            "percentage": percentage,
        }
    }


@router.get("/{batch_id}/results")
async def get_omr_results(
    batch_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(OMRSheet).where(OMRSheet.batch_id == batch_id)
    result = await db.execute(stmt)
    sheets = result.scalars().all()

    if not sheets:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    first = sheets[0]
    paper = await db.get(Paper, first.paper_id)
    bp = await db.get(Blueprint, paper.blueprint_id) if paper else None
    max_score = float(bp.total_questions) if bp else 0

    # Get results from first sheet that has one, or compute from last submission
    all_results = []
    total_correct = 0
    total_max = 0

    for sheet in sheets:
        result_stmt = select(OMRResult).where(OMRResult.omr_sheet_id == sheet.id)
        result = await db.execute(result_stmt)
        omr_res = result.scalar_one_or_none()

        if omr_res:
            detected = json.loads(omr_res.detected_answers) if omr_res.detected_answers else []
            all_results.extend(detected)
            total_correct += omr_res.raw_score or 0
            total_max += omr_res.max_score or 0

    if not all_results:
        # No results yet, return empty
        return {
            "batch_id": batch_id,
            "paper_id": first.paper_id,
            "results": [],
            "summary": {"correct": 0, "total": 0, "percentage": 0},
        }

    total_max = total_max or max_score
    percentage = round((total_correct / total_max * 100), 2) if total_max > 0 else 0

    return {
        "batch_id": batch_id,
        "paper_id": first.paper_id,
        "paper_name": paper.variant_label if paper else "Unknown",
        "results": all_results,
        "summary": {
            "correct": int(total_correct),
            "total": int(total_max),
            "percentage": percentage,
        },
    }

@router.post("/{batch_id}/scan-upload")
async def scan_omr_upload(
    batch_id: str,
    file: UploadFile = File(...),
    student_id: int | None = Form(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(OMRSheet).where(OMRSheet.batch_id == batch_id).limit(1)
    result = await db.execute(stmt)
    sheet = result.scalar_one_or_none()
    
    if not sheet:
        raise HTTPException(status_code=404, detail="Batch not found")
        
    paper = await db.get(Paper, sheet.paper_id)
    bp = await db.get(Blueprint, paper.blueprint_id) if paper else None
    total_q = bp.total_questions if bp else 30

    ext = file.filename.split('.')[-1].lower() if file.filename else ''
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        if ext == 'zip':
            scan_results = await OMRCVService.process_zip(tmp_path, total_q)
        elif ext == 'pdf':
            scan_results = await OMRCVService.process_pdf(tmp_path, total_q)
        else:
            res = await OMRCVService.process_image(tmp_path, total_q)
            scan_results = [res]
            
        evaluations = []
        if scan_results:
            # Get all available sheets for this batch (including evaluated to allow re-scans)
            available_stmt = select(OMRSheet).where(
                OMRSheet.batch_id == batch_id
            ).order_by(OMRSheet.id)
            if student_id:
                available_stmt = available_stmt.where(OMRSheet.student_id == student_id)
            available_res = await db.execute(available_stmt)
            available_sheets = available_res.scalars().all()
            
            for idx, scan_res in enumerate(scan_results):
                answers = scan_res.get("answers", [])
                metadata = scan_res.get("metadata", {})
                
                # Check if QR code contains a specific student_id, or if manual student_id is provided
                resolved_student_id = qr_student_id or student_id
                target_sheet = None
                
                if resolved_student_id:
                    # Find the specific sheet for this student
                    target_sheet = next((s for s in available_sheets if s.student_id == resolved_student_id), None)
                
                # Fallbacks if no student_id could be resolved or sheet wasn't found
                if not target_sheet:
                    # Filter out sheets that have already been evaluated
                    unassigned_sheets = [s for s in available_sheets if s.status != "evaluated"]
                    if unassigned_sheets:
                        target_sheet = unassigned_sheets[0]
                    else:
                        target_sheet = OMRSheet(
                            batch_id=batch_id,
                            paper_id=sheet.paper_id,
                            assessment_id=sheet.assessment_id,
                            student_id=resolved_student_id,
                            status="generated",
                        )
                        db.add(target_sheet)
                        await db.flush()
                
                if resolved_student_id and not target_sheet.student_id:
                    target_sheet.student_id = resolved_student_id
                
                # Mark as evaluated so it won't be picked up by the next iteration in fallback mode
                target_sheet.status = "evaluated"
                
                evaluation = await _evaluate_and_save_result(db, target_sheet, answers, user.id, float(total_q))
                evaluations.append(evaluation)
                
            await db.commit()
                
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
            
    return {
        "batch_id": batch_id,
        "scanned_sheets": scan_results,
        "evaluation": evaluation
    }

@router.get("/{batch_id}/student/{student_id}/download-reports")
async def download_student_reports(
    batch_id: str,
    student_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(OMRSheet).where(OMRSheet.batch_id == batch_id, OMRSheet.student_id == student_id).limit(1)
    result = await db.execute(stmt)
    sheet = result.scalar_one_or_none()
    
    if not sheet:
        raise HTTPException(status_code=404, detail="Batch not found")

    # Generate insights
    analytics_svc = LearningAnalyticsService()
    try:
        insights = await analytics_svc.generate_student_insights(db, student_id, assessment_id=sheet.assessment_id)
    except Exception as e:
        insights = {
            "strengths": [],
            "areas_for_improvement": [],
            "recommendations": [],
            "narrative": f"Error generating insights: {str(e)}"
        }

    # Prefer the OMR Result linked to the StudentResult if it exists, to ensure sync
    sr_stmt = select(StudentResult).where(
        StudentResult.student_id == student_id
    )
    if sheet.assessment_id:
        sr_stmt = sr_stmt.where(StudentResult.assessment_id == sheet.assessment_id)
    sr_res = await db.execute(sr_stmt)
    student_result = sr_res.scalar_one_or_none()

    omr_result = None
    if student_result and student_result.omr_result_id:
        omr_res = await db.execute(select(OMRResult).where(OMRResult.id == student_result.omr_result_id))
        omr_result = omr_res.scalar_one_or_none()
    
    # Fallback to just grabbing the OMRResult for this specific sheet
    if not omr_result:
        omr_res = await db.execute(select(OMRResult).where(OMRResult.omr_sheet_id == sheet.id))
        omr_result = omr_res.scalar_one_or_none()
    evaluated_answers = []
    score = 0
    max_score = 0
    if omr_result:
        evaluated_answers = json.loads(omr_result.detected_answers or "[]")
        score = omr_result.raw_score or 0
        max_score = omr_result.max_score or 0

    # Generate both PDFs
    try:
        results_pdf_path = await PDFReportService.generate_omr_results_report(
            db, student_id, batch_id, evaluated_answers, score, max_score
        )
        analytics_pdf_path = await PDFReportService.generate_student_report(
            db, student_id, report_id=1, insights=insights, assessment_id=sheet.assessment_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate PDFs: {str(e)}")

    from app.db.models.assessments import Student
    student = await db.get(Student, student_id)
    student_name = student.full_name if student else "Unknown"
    safe_name = student_name.replace(" ", "_")
    zip_filename = f"Reports_Student_{safe_name}.zip"
    zip_filepath = os.path.join(tempfile.gettempdir(), zip_filename)
    
    with zipfile.ZipFile(zip_filepath, 'w') as zipf:
        zipf.write(results_pdf_path, arcname=os.path.basename(results_pdf_path))
        zipf.write(analytics_pdf_path, arcname=os.path.basename(analytics_pdf_path))

    return FileResponse(zip_filepath, media_type="application/zip", filename=zip_filename)

@router.delete("/{batch_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_omr_session(
    batch_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.role not in ("admin", "deo", "principal", "teacher"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
        
    # Safely cascade deletes from the bottom up to avoid Postgres foreign key violations
    from sqlalchemy.future import select
    from app.db.models import OMRResult, StudentResult, CompetencyResult

    # 1. Get sheets
    sheet_result = await db.execute(select(OMRSheet.id).where(OMRSheet.batch_id == batch_id))
    sheet_ids = [row[0] for row in sheet_result.all()]

    if sheet_ids:
        # 2. Get results
        omr_res = await db.execute(select(OMRResult.id).where(OMRResult.omr_sheet_id.in_(sheet_ids)))
        omr_result_ids = [row[0] for row in omr_res.all()]

        if omr_result_ids:
            # 3. Get student results
            sr_res = await db.execute(select(StudentResult.id).where(StudentResult.omr_result_id.in_(omr_result_ids)))
            sr_ids = [row[0] for row in sr_res.all()]

            if sr_ids:
                # 4. Delete Competency Results
                await db.execute(sa_delete(CompetencyResult).where(CompetencyResult.student_result_id.in_(sr_ids)))
                # 5. Delete Student Results
                await db.execute(sa_delete(StudentResult).where(StudentResult.id.in_(sr_ids)))

            # 6. Delete OMR Results
            await db.execute(sa_delete(OMRResult).where(OMRResult.id.in_(omr_result_ids)))

        # 7. Delete Sheets
        await db.execute(sa_delete(OMRSheet).where(OMRSheet.id.in_(sheet_ids)))
        await db.commit()
    
    await log_audit_entry(
        db, user_id=user.id,
        action="delete", resource_type="omr_session",
        extra_data={"batch_id": batch_id}
    )
