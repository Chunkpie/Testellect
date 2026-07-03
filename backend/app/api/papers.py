from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.db.models.auth import User
from app.db.models.papers import Blueprint, Paper, PaperQuestion
from app.db.models.questions import QuestionBank

router = APIRouter()


def _school_scope_filter(model, user):
    if user.role in ("administrator", "deo"):
        return None
    return model.school_id == user.school_id


@router.get("")
async def list_papers(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Paper).order_by(Paper.created_at.desc())
    if user.role not in ("administrator", "deo") and user.school_id:
        school_bp_ids = select(Blueprint.id).where(Blueprint.school_id == user.school_id)
        stmt = stmt.where(Paper.blueprint_id.in_(school_bp_ids))
    result = await db.execute(stmt)
    papers = result.scalars().all()

    items = []
    for p in papers:
        bp = await db.get(Blueprint, p.blueprint_id)
        items.append({
            "id": p.id,
            "name": p.variant_label,
            "grade": bp.grade if bp else 0,
            "subject_id": bp.subject_id if bp else 0,
            "total_marks": float(bp.total_marks) if bp else 0,
            "total_questions": bp.total_questions if bp else 0,
            "duration_minutes": bp.duration_minutes or 0,
            "school_id": bp.school_id if bp else 0,
            "created_by": p.generated_by,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        })
    return {"items": items, "total": len(items)}


@router.get("/{paper_id}")
async def get_paper_detail(
    paper_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Paper).where(Paper.id == paper_id))
    paper = result.scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found")

    bp_result = await db.execute(select(Blueprint).where(Blueprint.id == paper.blueprint_id))
    blueprint = bp_result.scalar_one_or_none()

    scope = _school_scope_filter(Blueprint, user)
    if scope is not None and blueprint and blueprint.school_id != user.school_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    pqs_result = await db.execute(
        select(PaperQuestion).where(PaperQuestion.paper_id == paper_id).order_by(PaperQuestion.sequence)
    )
    paper_questions = pqs_result.scalars().all()

    questions = []
    for pq in paper_questions:
        q_result = await db.execute(select(QuestionBank).where(QuestionBank.id == pq.question_id))
        q = q_result.scalar_one_or_none()
        if q:
            questions.append({
                "id": pq.id,
                "question_id": q.id,
                "sequence": pq.sequence,
                "question_text": q.question_text_en,
                "bloom_level": q.bloom_level,
                "difficulty": q.difficulty,
                "marks": float(q.marks) if q.marks else 1.0,
            })

    return {
        "id": paper.id,
        "name": paper.variant_label,
        "blueprint_id": paper.blueprint_id,
        "grade": blueprint.grade if blueprint else 0,
        "subject_id": blueprint.subject_id if blueprint else 0,
        "total_marks": float(blueprint.total_marks) if blueprint else 0,
        "total_questions": blueprint.total_questions if blueprint else 0,
        "duration_minutes": blueprint.duration_minutes or 0,
        "school_id": blueprint.school_id if blueprint else 0,
        "created_by": paper.generated_by,
        "created_at": paper.created_at.isoformat() if paper.created_at else None,
        "questions": questions,
    }


@router.get("/{paper_id}/export")
async def export_paper_pdf(
    paper_id: int,
    lang: str = "english",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from fastapi.responses import StreamingResponse
    from app.services.pdf_paper_service import PDFPaperService
    from app.db.models.image_bank import ImageAsset
    from app.db.models.questions import QuestionOption

    result = await db.execute(select(Paper).where(Paper.id == paper_id))
    paper = result.scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    bp_result = await db.execute(select(Blueprint).where(Blueprint.id == paper.blueprint_id))
    blueprint = bp_result.scalar_one_or_none()

    scope = _school_scope_filter(Blueprint, user)
    if scope is not None and blueprint and blueprint.school_id != user.school_id:
        raise HTTPException(status_code=403, detail="Access denied")

    pqs_result = await db.execute(
        select(PaperQuestion).where(PaperQuestion.paper_id == paper_id).order_by(PaperQuestion.sequence)
    )
    paper_questions = pqs_result.scalars().all()

    questions = []
    for pq in paper_questions:
        q_result = await db.execute(select(QuestionBank).where(QuestionBank.id == pq.question_id))
        q = q_result.scalar_one_or_none()
        if q:
            # Get Image
            image_path = None
            if q.image_asset_id:
                img_res = await db.execute(select(ImageAsset).where(ImageAsset.id == q.image_asset_id))
                img = img_res.scalar_one_or_none()
                if img:
                    image_path = img.file_path
                    
            # Get Options
            opts_res = await db.execute(
                select(QuestionOption).where(QuestionOption.question_id == q.id).order_by(QuestionOption.sequence)
            )
            opts = opts_res.scalars().all()
            
            # Map option order
            order = []
            if pq.option_order:
                import json
                try:
                    order = json.loads(pq.option_order)
                except:
                    pass
                    
            ordered_opts = opts
            if order and len(order) == len(opts):
                ordered_opts = [opts[i] for i in order]

            options_list = []
            prefixes = ['A)', 'B)', 'C)', 'D)']
            for i, opt in enumerate(ordered_opts):
                options_list.append({
                    "option_text_en": opt.option_text_en,
                    "option_text_hi": opt.option_text_hi,
                    "option_text_gu": opt.option_text_gu,
                    "prefix": prefixes[i] if i < len(prefixes) else "•"
                })

            questions.append({
                "sequence": pq.sequence,
                "question_text_en": q.question_text_en,
                "question_text_hi": q.question_text_hi,
                "question_text_gu": q.question_text_gu,
                "image_path": image_path,
                "options": options_list
            })

    paper_info = {
        "name": paper.variant_label,
        "grade": blueprint.grade if blueprint else 0,
        "subject_id": blueprint.subject_id if blueprint else 0,
        "total_marks": float(blueprint.total_marks) if blueprint else 0,
        "duration_minutes": blueprint.duration_minutes or 0,
    }

    pdf_service = PDFPaperService()
    pdf_buffer = pdf_service.generate_paper_pdf(paper_info, questions, language=lang)
    
    filename = f"Paper_{paper_id}_{lang}.pdf"
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
