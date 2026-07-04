import asyncio
import logging
import random
from datetime import datetime, timezone
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.curriculum import Book, Chapter, Concept, Topic, Subject
from app.db.models.questions import QuestionBank
from app.db.models.papers import Blueprint, Paper, PaperQuestion

logger = logging.getLogger(__name__)

async def create_blueprint_and_papers(
    db: AsyncSession,
    book_id: int,
    user_id: int,
    school_id: int,
    questions: list[QuestionBank],
    num_papers: int = 15,
    questions_per_paper: int = 40
):
    # Fetch book and subject
    b_res = await db.execute(select(Book).where(Book.id == book_id))
    book = b_res.scalar_one_or_none()
    if not book:
        return
        
    s_res = await db.execute(select(Subject).where(Subject.id == book.subject_id))
    subject = s_res.scalar_one_or_none()
    sub_name = subject.name_en if subject else "General"
    
    # Create Blueprint
    bp = Blueprint(
        school_id=school_id,
        created_by=user_id,
        name=f"{sub_name} Grade {book.grade} AI Auto-Generated",
        grade=book.grade,
        subject_id=book.subject_id,
        total_questions=questions_per_paper,
        total_marks=float(questions_per_paper),
        duration_minutes=60,
    )
    db.add(bp)
    await db.flush()
    
    # Create 15 Papers
    for i in range(num_papers):
        paper = Paper(
            blueprint_id=bp.id,
            variant_label=f"Paper {i+1}",
            generated_at=datetime.utcnow(),
            generated_by=user_id,
        )
        db.add(paper)
        await db.flush()
        
        # Shuffle all generated questions and pick top N
        paper_qs = list(questions)
        random.shuffle(paper_qs)
        selected_qs = paper_qs[:questions_per_paper]
        
        for seq, q in enumerate(selected_qs):
            pq = PaperQuestion(
                paper_id=paper.id,
                question_id=q.id,
                sequence=seq + 1,
            )
            db.add(pq)
            
    await db.commit()
    logger.info(f"Successfully generated {num_papers} papers with {questions_per_paper} questions each.")
