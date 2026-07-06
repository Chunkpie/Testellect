import asyncio
import sys

sys.path.append("/app")

from sqlalchemy import select
from app.core.database import async_session_factory as SessionLocal
from app.db.models.curriculum import Subject, Book, Chapter, Concept, LearningOutcome
from app.db.models.questions import QuestionBank, QuestionOption

async def generate_dummy_questions():
    async with SessionLocal() as db:
        res = await db.execute(select(Book).where(Book.title == "Mathematics - Class 10"))
        book = res.scalar_one_or_none()
        if not book:
            return

        res = await db.execute(select(Chapter).where(Chapter.book_id == book.id))
        chapters = res.scalars().all()

        q_count = 0
        for chapter in chapters:
            from app.db.models.curriculum import Topic
            res = await db.execute(select(Topic).where(Topic.chapter_id == chapter.id))
            topics = res.scalars().all()
            for topic in topics:
                res = await db.execute(select(Concept).where(Concept.topic_id == topic.id))
                concepts = res.scalars().all()
            for concept in concepts:
                # Add 3 dummy questions per concept
                for i in range(3):
                    q = QuestionBank(
                        school_id=1,
                        concept_id=concept.id,
                        question_type="mcq",
                        question_text_en=f"Dummy question {i+1} for {concept.name_en}?",
                        bloom_level="apply" if i == 0 else ("understand" if i == 1 else "remember"),
                        difficulty="medium" if i == 0 else ("easy" if i == 1 else "hard"),
                        marks=1,
                        approval_status="approved"
                    )
                    db.add(q)
                    await db.flush()

                    for j in range(4):
                        opt = QuestionOption(
                            question_id=q.id,
                            option_text_en=f"Option {chr(65+j)}",
                            is_correct=(j == 0),
                            sequence=j+1
                        )
                        db.add(opt)
                    
                    q_count += 1
        
        await db.commit()
        print(f"Added {q_count} dummy questions!")

if __name__ == "__main__":
    asyncio.run(generate_dummy_questions())
