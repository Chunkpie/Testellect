import os
from datetime import timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_db, get_current_user
from app.models.models import User, Book, Chapter, Topic, Concept
from app.services.ai_service import AiService

router = APIRouter()


def _to_utc_iso(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc).isoformat()
    return dt.isoformat()


class BookResponse(BaseModel):
    id: int
    title: str
    grade: int
    subject_id: int
    processing_status: str
    processing_error: str | None
    file_path: str
    chapters: list[dict[str, Any]] = []
    created_at: str | None = None


class BookListItem(BaseModel):
    id: int
    title: str
    grade: int
    subject_id: int
    processing_status: str
    processing_error: str | None
    created_at: str | None = None


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_book(
    file: UploadFile = File(...),
    title: str = Form(...),
    grade: int = Form(...),
    subject_id: int = Form(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.db.models.curriculum import Book as BookModel
    import hashlib

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    file_bytes = await file.read()
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    safe_name = f"{file_hash}_{file.filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, safe_name)

    with open(file_path, "wb") as f:
        f.write(file_bytes)

    book = BookModel(
        school_id=user.school_id,
        subject_id=subject_id,
        grade=grade,
        title=title,
        file_path=file_path,
        source_type="pdf",
        processing_status="uploaded",
        uploaded_by=user.id if hasattr(user, "id") else None,
    )
    db.add(book)
    await db.commit()
    await db.refresh(book)

    return {
        "id": book.id,
        "title": book.title,
        "grade": book.grade,
        "subject_id": book.subject_id,
        "processing_status": book.processing_status,
        "message": "Book uploaded successfully",
    }


@router.get("")
async def list_books(
    grade: int | None = Query(None),
    subject_id: int | None = Query(None),
    processing_status: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Book)
    if grade is not None:
        stmt = stmt.where(Book.grade == grade)
    if subject_id is not None:
        stmt = stmt.where(Book.subject_id == subject_id)
    if processing_status is not None:
        stmt = stmt.where(Book.processing_status == processing_status)
    stmt = stmt.order_by(Book.created_at.desc())
    result = await db.execute(stmt)
    books = result.scalars().all()

    items = []
    for b in books:
        items.append(BookListItem(
            id=b.id,
            title=b.title,
            grade=b.grade,
            subject_id=b.subject_id,
            processing_status=b.processing_status or "uploaded",
            processing_error=b.processing_error,
            created_at=_to_utc_iso(b.created_at),
        ))
    return {"items": items, "total": len(items)}


@router.get("/{book_id}")
async def get_book(
    book_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Book).where(Book.id == book_id))
    book = result.scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    chapters_result = await db.execute(
        select(Chapter).where(Chapter.book_id == book_id).order_by(Chapter.sequence)
    )
    chapters = chapters_result.scalars().all()
    chapters_data = []
    for ch in chapters:
        topics_result = await db.execute(
            select(Topic).where(Topic.chapter_id == ch.id).order_by(Topic.sequence)
        )
        topics = topics_result.scalars().all()
        chapters_data.append({
            "id": ch.id,
            "title_en": ch.title_en,
            "unit_name": ch.unit_name,
            "sequence": ch.sequence,
            "topics": [{"id": t.id, "title_en": t.title_en, "sequence": t.sequence} for t in topics],
        })

    return BookResponse(
        id=book.id,
        title=book.title,
        grade=book.grade,
        subject_id=book.subject_id,
        processing_status=book.processing_status or "uploaded",
        processing_error=book.processing_error,
        file_path=book.file_path,
        chapters=chapters_data,
        created_at=_to_utc_iso(book.created_at),
    )


@router.get("/{book_id}/status")
async def get_book_status(
    book_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Book).where(Book.id == book_id))
    book = result.scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    return {
        "id": book.id,
        "processing_status": book.processing_status or "uploaded",
        "processing_error": book.processing_error,
    }


@router.post("/{book_id}/extract")
async def extract_book_text(
    book_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Book).where(Book.id == book_id))
    book = result.scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    if not book.file_path or not os.path.exists(book.file_path):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File not found")

    ai = AiService()
    extract_result = await ai.extract_text_only(db, book_id)
    if not extract_result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=extract_result.get("error", "Text extraction failed"),
        )

    return {
        "id": book.id,
        "status": book.processing_status,
        "chunks_created": extract_result.get("chunks_created", 0),
        "message": "Text extracted successfully",
    }


@router.post("/{book_id}/analyze")
async def analyze_book(
    book_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Book).where(Book.id == book_id))
    book = result.scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    ai = AiService()
    pipeline_result = await ai.analyze_book(db, book_id, user_id=str(user.id) if hasattr(user, "id") else None)

    return {
        "id": book.id,
        "status": book.processing_status,
        "job_id": pipeline_result.get("job_id"),
        "stages": pipeline_result.get("stages", {}),
        "success": pipeline_result.get("success", False),
        "message": "Pipeline completed" if pipeline_result.get("success") else "Pipeline completed with errors",
    }


@router.post("/{book_id}/generate-questions")
async def generate_questions_for_book(
    book_id: int,
    concept_id: int | None = Query(None),
    count: int = Query(5, ge=1, le=50),
    bloom_level: str = Query("understand"),
    difficulty: str = Query("medium"),
    question_type: str = Query("mcq"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Book).where(Book.id == book_id))
    book = result.scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    ai = AiService()

    if concept_id:
        try:
            questions = await ai.generate_questions(
                db=db,
                concept_id=concept_id,
                count=count,
                bloom_level=bloom_level,
                difficulty=difficulty,
                question_type=question_type,
                school_id=user.school_id,
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    else:
        concepts_result = await db.execute(
            select(Concept)
            .join(Concept.topic)
            .join(Topic.chapter)
            .where(Chapter.book_id == book_id)
        )
        concepts = concepts_result.scalars().all()
        questions = []
        for c in concepts[:5]:
            try:
                qs = await ai.generate_questions(
                    db=db,
                    concept_id=c.id,
                    count=max(1, count // 5),
                    bloom_level=bloom_level,
                    difficulty=difficulty,
                    question_type=question_type,
                    school_id=user.school_id,
                )
                questions.extend(qs)
            except ValueError:
                continue

    return {
        "book_id": book_id,
        "questions_generated": len(questions),
        "questions": questions[:count],
    }
