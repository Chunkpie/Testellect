import json
import os
import time
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit_entry
from app.core.deps import get_current_user, get_db
from app.db.models.assessments import Assessment
from app.db.models.auth import User
from app.db.models.omr import OMRResult, OMRSheet
from app.db.models.papers import Paper, PaperQuestion, Blueprint
from app.db.models.questions import QuestionOption
from app.services.omr_service import generate_omr_pdf
from app.services.omr_cv_service import OMRCVService
import tempfile
import shutil

router = APIRouter()


@router.get("")
async def list_omr_sessions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(OMRSheet.batch_id, OMRSheet.paper_id, OMRSheet.created_at, func.count(OMRSheet.id).label("sheet_count"))
        .where(OMRSheet.batch_id.is_not(None))
        .group_by(OMRSheet.batch_id, OMRSheet.paper_id, OMRSheet.created_at)
        .order_by(OMRSheet.created_at.desc())
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
    student_count: int


@router.post("/generate")
async def generate_omr(
    req: GenerateOMRRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    paper_id = req.paper_id
    student_count = req.student_count
    paper = await db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found")

    blueprint = await db.get(Blueprint, paper.blueprint_id)
    if not blueprint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blueprint not found")

    batch_id = _compute_session_id()

    # Find or create an assessment for this paper
    stmt = select(Assessment).where(
        Assessment.blueprint_id == paper.blueprint_id,
        Assessment.school_id == user.school_id,
    ).order_by(Assessment.created_at.desc()).limit(1)
    result = await db.execute(stmt)
    assessment = result.scalar_one_or_none()

    if not assessment:
        assessment = Assessment(
            school_id=user.school_id or blueprint.school_id,
            blueprint_id=paper.blueprint_id,
            class_id=1,
            name=f"OMR - {paper.variant_label}",
            status="scheduled",
        )
        db.add(assessment)
        await db.flush()

    # Create a template OMRSheet record for this batch
    sheet = OMRSheet(
        paper_id=paper_id,
        assessment_id=assessment.id,
        student_id=None,
        qr_payload=batch_id,
        sheet_pdf_path=None,
        status="generated",
        batch_id=batch_id,
    )
    db.add(sheet)
    await db.flush()
    sheets_created = [{"id": sheet.id, "student_number": 1}]

    await db.commit()

    await log_audit_entry(
        db=db,
        user_id=user.id,
        school_id=user.school_id,
        action="generate_omr",
        resource_type="omr_sheet",
        extra_data={"paper_id": paper_id, "student_count": student_count, "batch_id": batch_id},
    )

    return {
        "batch_id": batch_id,
        "paper_id": paper_id,
        "paper_name": paper.variant_label,
        "student_count": 0,
        "file_path": None,
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

    sheet_list = []
    for s in sheets:
        sheet_list.append({
            "id": s.id,
            "student_id": s.student_id,
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

    return FileResponse(filepath, media_type="application/x-custom-pdf", filename=filename)


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
        .where(PaperQuestion.paper_id == first.paper_id)
        .order_by(PaperQuestion.sequence)
    )
    result = await db.execute(pq_stmt)
    paper_questions = result.scalars().all()

    correct_answers: dict[int, dict] = {}
    answer_key: dict[int, str] = {}
    for pq in paper_questions:
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
            "sequence": pq.sequence,
            "correct_answer": correct_letter or "",
            "options": [{"text": o.option_text_en, "letter": order[i] if i < len(order) else chr(65 + i)}
                        for i, o in enumerate(options)],
        }
        answer_key[question_key] = correct_letter or ""

    # Evaluate answers
    evaluated_answers = []
    for ans in answers:
        qid = ans.get("question_id")
        student_ans = ans.get("answer", "").strip().upper()
        sequence = None

        # Find which sequence this question_id maps to
        for k, v in correct_answers.items():
            if v["question_id"] == qid:
                sequence = v["sequence"]
                break

        if sequence is None:
            continue

        correct = answer_key.get(sequence, "")
        is_correct = student_ans == correct
        if is_correct:
            correct_count += 1

        evaluated_answers.append({
            "question_id": qid,
            "sequence": sequence,
            "student_answer": student_ans,
            "correct_answer": correct,
            "is_correct": is_correct,
        })

    score = correct_count
    percentage = round((score / max_score * 100), 2) if max_score > 0 else 0

    # Create OMRResult records for each sheet (or just one for the batch)
    for sheet in sheets:
        existing = await db.get(OMRResult, sheet.id)
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
            
        # If Option A was used and student_id is provided, evaluate immediately
        evaluation = None
        if student_id and scan_results and len(scan_results) == 1:
            answers = scan_results[0].get("answers", [])
            # Find an available sheet for this student
            sheet_stmt = select(OMRSheet).where(
                OMRSheet.batch_id == batch_id,
                (OMRSheet.student_id == student_id) | (OMRSheet.student_id.is_(None))
            ).limit(1)
            sheet_res = await db.execute(sheet_stmt)
            target_sheet = sheet_res.scalar_one_or_none()
            if not target_sheet:
                target_sheet = OMRSheet(
                    batch_id=batch_id,
                    paper_id=sheet.paper_id,
                    assessment_id=sheet.assessment_id,
                    student_id=student_id,
                    status="generated",
                )
                db.add(target_sheet)
                await db.flush()
            
            if target_sheet:
                target_sheet.student_id = student_id
                evaluation = await _evaluate_and_save_result(db, target_sheet, answers, user.id, float(total_q))
                await db.commit()
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
            
    return {
        "batch_id": batch_id,
        "scanned_sheets": scan_results,
        "evaluation": evaluation
    }
