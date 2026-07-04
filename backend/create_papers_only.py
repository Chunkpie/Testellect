import asyncio
from app.core.database import async_session_factory
from app.db.models.questions import QuestionBank
from app.db.models.papers import Blueprint, Paper, PaperQuestion
from app.db.models.curriculum import Book, Chapter, Topic, Concept
from sqlalchemy import select
from datetime import datetime
import random

async def run():
    async with async_session_factory() as db:
        book_id = 3
        questions_per_paper = 40
        num_papers = 15
        user_id = 2  # default user id

        # Get the book
        result = await db.execute(select(Book).where(Book.id == book_id))
        book = result.scalar_one_or_none()
        
        # Get all questions for this book
        stmt = (
            select(QuestionBank)
            .join(Concept)
            .join(Topic)
            .join(Chapter)
            .where(Chapter.book_id == book_id)
        )
        result = await db.execute(stmt)
        questions = result.scalars().all()
        
        if not questions:
            print("No questions found for this book!")
            return
            
        print(f"Found {len(questions)} questions. Creating Blueprint...")
        
        # Create Blueprint
        bp = Blueprint(
            school_id=2,  # Default
            created_by=user_id,
            name=f"Math Grade {book.grade} AI Auto-Generated",
            grade=book.grade,
            subject_id=book.subject_id,
            total_questions=questions_per_paper,
            total_marks=float(questions_per_paper),
        )
        db.add(bp)
        await db.flush()
        
        print("Creating 15 papers...")
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
            
            # Associate questions with the paper
            for seq, q in enumerate(selected_qs, start=1):
                pq = PaperQuestion(
                    paper_id=paper.id,
                    question_id=q.id,
                    sequence=seq,
                )
                db.add(pq)
                
            await db.flush()
            
        await db.commit()
        print("Done! Papers created successfully.")

if __name__ == "__main__":
    asyncio.run(run())
