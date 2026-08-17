from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.core.audit import log_audit_entry
from app.models.models import (
    User,
    Subject,
    Book,
    Chapter,
    Topic,
    Concept,
    LearningOutcome,
    Competency,
)

router = APIRouter()


@router.get("/tree")
async def get_knowledge_tree(
    grade: int | None = Query(None),
    subject_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("teacher", "administrator"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )

    stmt = select(Subject)
    if grade is not None:
        stmt = stmt.where(Subject.grade == grade)
    if subject_id is not None:
        stmt = stmt.where(Subject.id == subject_id)
    stmt = stmt.order_by(Subject.grade, Subject.name_en)
    result = await db.execute(stmt)
    subjects = result.scalars().all()

    tree = []
    for subj in subjects:
        book_stmt = select(Book).where(Book.subject_id == subj.id)
        if grade is not None:
            book_stmt = book_stmt.where(Book.grade == grade)
        book_result = await db.execute(book_stmt)
        books = book_result.scalars().all()

        subject_node = {
            "id": subj.id,
            "name_en": subj.name_en,
            "name_hi": subj.name_hi,
            "name_gu": subj.name_gu,
            "grade": subj.grade,
            "books": [],
        }

        for book in books:
            chap_result = await db.execute(
                select(Chapter)
                .where(Chapter.book_id == book.id)
                .order_by(Chapter.sequence)
            )
            chapters = chap_result.scalars().all()

            book_node = {
                "id": book.id,
                "title": book.title,
                "grade": book.grade,
                "chapters": [],
            }

            for ch in chapters:
                topic_result = await db.execute(
                    select(Topic)
                    .where(Topic.chapter_id == ch.id)
                    .order_by(Topic.sequence)
                )
                topics = topic_result.scalars().all()

                chapter_node = {
                    "id": ch.id,
                    "title_en": ch.title_en,
                    "title_hi": ch.title_hi,
                    "title_gu": ch.title_gu,
                    "unit_name": ch.unit_name,
                    "sequence": ch.sequence,
                    "topics": [],
                }

                for t in topics:
                    concept_result = await db.execute(
                        select(Concept)
                        .where(Concept.topic_id == t.id)
                        .order_by(Concept.name_en)
                    )
                    concepts = concept_result.scalars().all()

                    topic_node = {
                        "id": t.id,
                        "title_en": t.title_en,
                        "sequence": t.sequence,
                        "concepts": [],
                    }

                    for c in concepts:
                        lo_result = await db.execute(
                            select(LearningOutcome).where(
                                LearningOutcome.concept_id == c.id
                            )
                        )
                        los = lo_result.scalars().all()

                        concept_node = {
                            "id": c.id,
                            "name_en": c.name_en,
                            "name_hi": c.name_hi,
                            "name_gu": c.name_gu,
                            "description": c.description,
                            "learning_outcomes": [
                                {
                                    "id": lo.id,
                                    "code": lo.code,
                                    "description_en": lo.description_en,
                                }
                                for lo in los
                            ],
                        }
                        topic_node["concepts"].append(concept_node)

                    chapter_node["topics"].append(topic_node)

                book_node["chapters"].append(chapter_node)

            subject_node["books"].append(book_node)

        tree.append(subject_node)

    return {"items": tree}


@router.get("/search")
async def search_knowledge_base(
    q: str = Query(""),
    grade: int | None = Query(None),
    subject_id: int | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("teacher", "administrator"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )

    from app.models.models import KnowledgeChunk

    stmt = select(KnowledgeChunk)

    if subject_id is not None:
        stmt = stmt.join(Book).where(Book.subject_id == subject_id)
    if grade is not None:
        stmt = stmt.join(Book).where(Book.grade == grade)
    if q:
        stmt = stmt.where(KnowledgeChunk.chunk_text.ilike(f"%{q}%"))

    stmt = stmt.limit(limit)
    result = await db.execute(stmt)
    chunks = result.scalars().all()

    return {"items": chunks, "total": len(chunks)}


@router.get("/concepts/{concept_id}")
async def get_concept(
    concept_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("teacher", "administrator"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )

    result = await db.execute(select(Concept).where(Concept.id == concept_id))
    concept = result.scalar_one_or_none()
    if not concept:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Concept not found"
        )

    lo_result = await db.execute(
        select(LearningOutcome).where(LearningOutcome.concept_id == concept_id)
    )
    learning_outcomes = lo_result.scalars().all()

    comp_result = await db.execute(
        select(Competency)
        .join("learning_outcome_competencies")
        .join(LearningOutcome)
        .where(LearningOutcome.concept_id == concept_id)
    )
    competencies = comp_result.scalars().all()

    return {
        "id": concept.id,
        "name_en": concept.name_en,
        "name_hi": concept.name_hi,
        "name_gu": concept.name_gu,
        "description": concept.description,
        "extracted_by": concept.extracted_by,
        "learning_outcomes": [
            {"id": lo.id, "code": lo.code, "description_en": lo.description_en}
            for lo in learning_outcomes
        ],
        "competencies": [
            {"id": c.id, "name_en": c.name_en, "nas_parakh_code": c.nas_parakh_code}
            for c in competencies
        ],
    }


class ConceptUpdate(BaseModel):
    name_en: str | None = None
    name_hi: str | None = None
    name_gu: str | None = None
    description: str | None = None


@router.patch("/concepts/{concept_id}")
async def update_concept(
    concept_id: int,
    data: ConceptUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("teacher", "administrator"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )

    result = await db.execute(select(Concept).where(Concept.id == concept_id))
    concept = result.scalar_one_or_none()
    if not concept:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Concept not found"
        )

    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(concept, key, val)

    await db.commit()
    await db.refresh(concept)

    await log_audit_entry(
        db=db,
        user_id=current_user.id,
        school_id=current_user.school_id,
        action="update",
        resource_type="concept",
        resource_id=concept_id,
    )

    return concept


@router.get("/competencies")
async def list_competencies(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Competency).order_by(Competency.name_en))
    competencies = result.scalars().all()
    return {"items": competencies}
