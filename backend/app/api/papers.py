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
@router.get("/{paper_id}/download")
async def export_paper_pdf(
    paper_id: int,
    lang: str = "english",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from fastapi.responses import Response
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

    from app.services.translation_service import translate_paper_questions
    await translate_paper_questions(db, paper_id, lang)

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
                ordered_opts = [opts[int(i)] for i in order]

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

    from app.db.models.curriculum import Subject
    subject = await db.get(Subject, blueprint.subject_id) if blueprint else None
    
    paper_info = {
        "name": paper.variant_label,
        "grade": blueprint.grade if blueprint else 0,
        "subject_id": blueprint.subject_id if blueprint else 0,
        "subject_name": subject.name_en if subject else "General",
        "total_marks": float(blueprint.total_marks) if blueprint else 0,
        "duration_minutes": blueprint.duration_minutes or 0,
    }

    pdf_service = PDFPaperService()
    pdf_buffer = pdf_service.generate_paper_pdf(paper_info, questions, language=lang)
    
    filename = f"Paper_{paper_id}_{lang}.pdf"
    
    return Response(
        content=pdf_buffer.getvalue(),
        media_type="application/x-custom-pdf"
    )

from pydantic import BaseModel
from typing import List
import random
from app.db.models.curriculum import Topic, Concept
from app.core.constants import ApprovalStatus

class CustomPaperRequest(BaseModel):
    grade: int
    subject_id: int
    chapter_ids: List[int]
    total_questions: int
    difficulty: str = "medium"

@router.post("/custom-generate")
async def generate_custom_paper(
    req: CustomPaperRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if user.role not in ("teacher", "administrator"):
        raise HTTPException(status_code=403, detail="Not allowed")

    topic_res = await db.execute(select(Topic.id).where(Topic.chapter_id.in_(req.chapter_ids)))
    topic_ids = topic_res.scalars().all()
    if not topic_ids:
        raise HTTPException(status_code=400, detail="No topics found for these chapters")

    concept_res = await db.execute(select(Concept.id).where(Concept.topic_id.in_(topic_ids)))
    concept_ids = concept_res.scalars().all()
    if not concept_ids:
        raise HTTPException(status_code=400, detail="No concepts found for these chapters")

    # Distribute the total_questions across a subset of concepts
    import random
    from app.services.ai_service import AiService
    
    num_concepts_to_use = min(len(concept_ids), req.total_questions)
    chosen_concepts = random.sample(concept_ids, num_concepts_to_use)
    
    base_count = req.total_questions // num_concepts_to_use
    remainder = req.total_questions % num_concepts_to_use
    
    ai_service = AiService()
    generated_question_ids = []
    
    import asyncio
    from app.core.database import async_session_factory
    
    sem = asyncio.Semaphore(3)

    async def generate_for_concept(cid, count):
        async with sem:
            async with async_session_factory() as session:
                return await ai_service.generate_questions_batched(
                    db=session,
                    concept_id=cid,
                    total_count=count,
                    difficulty=req.difficulty,
                    school_id=user.school_id
                )

    tasks = []
    for i, cid in enumerate(chosen_concepts):
        count = base_count + (1 if i < remainder else 0)
        tasks.append(generate_for_concept(cid, count))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    for res in results:
        if isinstance(res, Exception):
            print(f"Error in generation task: {res}")
            continue
        for nq in res:
            if "id" in nq:
                generated_question_ids.append(nq["id"])
                
    if not generated_question_ids:
        raise HTTPException(status_code=500, detail="AI failed to generate questions.")

    import json
    bp = Blueprint(
        school_id=user.school_id,
        name=f"Custom Blueprint - Grade {req.grade}",
        grade=req.grade,
        subject_id=req.subject_id,
        total_marks=float(len(generated_question_ids)),
        total_questions=len(generated_question_ids),
        duration_minutes=len(generated_question_ids) * 2,
        bloom_distribution="{}",
        difficulty_distribution="{}",
        chapter_ids=json.dumps(req.chapter_ids)
    )
    db.add(bp)
    await db.flush()

    paper = Paper(
        blueprint_id=bp.id,
        variant_label=f"Custom Paper - Grade {req.grade}",
        generated_by=user.id
    )
    db.add(paper)
    await db.flush()
    
    from app.db.models.papers import PaperQuestion
    for i, q_id in enumerate(generated_question_ids):
        pq = PaperQuestion(
            paper_id=paper.id,
            question_id=q_id,
            sequence=i+1
        )
        db.add(pq)

    await db.commit()
    return {"message": "Paper generated successfully", "paper_id": paper.id}
