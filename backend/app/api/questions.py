from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.deps import get_db, get_current_user
from app.core.constants import ApprovalStatus
from app.models.models import (
    User,
    QuestionBank,
    QuestionOption,
    Concept,
    Topic,
    Chapter,
)


def _to_utc_iso(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc).isoformat()
    return dt.isoformat()


router = APIRouter()


@router.get("")
async def list_questions(
    status: Optional[str] = Query(None, alias="approval_status"),
    difficulty: Optional[str] = None,
    bloom_level: Optional[str] = None,
    question_type: Optional[str] = None,
    concept_id: Optional[int] = None,
    book_id: Optional[int] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(QuestionBank)
    if current_user.school_id:
        stmt = stmt.where(QuestionBank.school_id == current_user.school_id)
    if status:
        stmt = stmt.where(QuestionBank.approval_status == status)
    if difficulty:
        stmt = stmt.where(QuestionBank.difficulty == difficulty)
    if bloom_level:
        stmt = stmt.where(QuestionBank.bloom_level == bloom_level)
    if question_type:
        stmt = stmt.where(QuestionBank.question_type == question_type)
    if concept_id:
        stmt = stmt.where(QuestionBank.concept_id == concept_id)
    if book_id:
        stmt = (
            stmt.join(Concept, Concept.id == QuestionBank.concept_id)
            .join(Topic, Topic.id == Concept.topic_id)
            .join(Chapter, Chapter.id == Topic.chapter_id)
            .where(Chapter.book_id == book_id)
        )
    stmt = stmt.where(QuestionBank.is_deleted == False)
    stmt = stmt.options(
        joinedload(QuestionBank.image), selectinload(QuestionBank.options)
    )
    stmt = stmt.order_by(QuestionBank.created_at.desc())

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar()

    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    questions = result.scalars().all()

    items = []
    for q in questions:
        options = sorted(q.options, key=lambda x: x.sequence)
        items.append(
            {
                "id": q.id,
                "school_id": q.school_id,
                "question_text_en": q.question_text_en,
                "question_type": q.question_type,
                "bloom_level": q.bloom_level,
                "difficulty": q.difficulty,
                "marks": q.marks,
                "concept_id": q.concept_id,
                "competency_id": q.competency_id,
                "approval_status": q.approval_status,
                "image_asset_id": q.image_asset_id,
                "image_url": q.image.file_path if q.image else None,
                "confidence_score": q.confidence_score,
                "options": [
                    {
                        "id": o.id,
                        "option_text_en": o.option_text_en,
                        "is_correct": o.is_correct,
                        "sequence": o.sequence,
                    }
                    for o in options
                ],
                "created_at": _to_utc_iso(q.created_at) or "",
            }
        )

    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/{question_id}")
async def get_question(question_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(QuestionBank)
        .options(joinedload(QuestionBank.image), selectinload(QuestionBank.options))
        .where(QuestionBank.id == question_id)
    )
    q = result.scalar_one_or_none()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    options = sorted(q.options, key=lambda x: x.sequence)
    return {
        "id": q.id,
        "school_id": q.school_id,
        "question_text_en": q.question_text_en,
        "question_type": q.question_type,
        "bloom_level": q.bloom_level,
        "difficulty": q.difficulty,
        "marks": q.marks,
        "concept_id": q.concept_id,
        "competency_id": q.competency_id,
        "approval_status": q.approval_status,
        "image_asset_id": q.image_asset_id,
        "image_url": q.image.file_path if q.image else None,
        "confidence_score": q.confidence_score,
        "options": [
            {
                "id": o.id,
                "option_text_en": o.option_text_en,
                "is_correct": o.is_correct,
                "sequence": o.sequence,
            }
            for o in options
        ],
        "created_at": q.created_at.isoformat() if q.created_at else "",
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_question(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Manual question creation not yet implemented",
    )


@router.post("/bulk-action")
async def bulk_action(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Bulk actions not yet implemented",
    )


@router.post("/{question_id}/approve")
async def approve_question(
    question_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(QuestionBank).where(QuestionBank.id == question_id)
    )
    q = result.scalar_one_or_none()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    q.approval_status = ApprovalStatus.APPROVED
    await db.commit()
    return {"status": "approved"}


@router.post("/{question_id}/reject")
async def reject_question(
    question_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(QuestionBank).where(QuestionBank.id == question_id)
    )
    q = result.scalar_one_or_none()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    q.approval_status = ApprovalStatus.REJECTED
    await db.commit()
    return {"status": "rejected"}


from pydantic import BaseModel


class QuestionPatch(BaseModel):
    image_asset_id: Optional[int] = None
    remove_image: Optional[bool] = False


@router.patch("/{question_id}")
async def patch_question(
    question_id: int,
    payload: QuestionPatch,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(QuestionBank).where(QuestionBank.id == question_id)
    )
    q = result.scalar_one_or_none()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")

    if payload.remove_image:
        q.image_asset_id = None
    elif payload.image_asset_id is not None:
        q.image_asset_id = payload.image_asset_id

    await db.commit()
    return {"status": "updated"}
