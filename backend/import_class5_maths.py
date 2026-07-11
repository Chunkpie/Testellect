import asyncio
import json
import os
import sys

# Add backend directory to sys.path so we can import app modules
sys.path.append("/app")

from sqlalchemy import select
from app.core.database import async_session_factory as SessionLocal
from app.db.models.curriculum import Subject, Book, Chapter, Topic, Concept, LearningOutcome

JSON_DIR = "./Curriculum/Class 5/Maths"

async def import_json():
    async with SessionLocal() as db:
        # Check if Mathematics subject exists
        res = await db.execute(select(Subject).where(Subject.name_en == "Mathematics"))
        subject = res.scalar_one_or_none()
        if not subject:
            subject = Subject(name_en="Mathematics", code="MATH")
            db.add(subject)
            await db.flush()

        # Check if the book exists, else create it
        res = await db.execute(select(Book).where(Book.title == "Mathematics - Class 5"))
        book = res.scalar_one_or_none()
        if not book:
            book = Book(
                title="Mathematics - Class 5",
                grade=5,
                subject_id=subject.id,
                file_path=JSON_DIR, # Dummy path
                processing_status="ready"
            )
            db.add(book)
            await db.flush()

        # Read all JSON files
        files = [f for f in os.listdir(JSON_DIR) if f.endswith(".json")]
        print(f"Found {len(files)} JSON files in {JSON_DIR}")
        for file in files:
            path = os.path.join(JSON_DIR, file)
            print(f"Importing {file}...")
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            chapters_data = data.get("chapters", [])
            if not chapters_data and "title" in data and "topics" in data:
                chapters_data = [data]
                
            for c_data in chapters_data:
                # Check if chapter exists
                res = await db.execute(select(Chapter).where(Chapter.book_id == book.id, Chapter.title_en == c_data["title"]))
                chapter = res.scalar_one_or_none()
                if not chapter:
                    chapter = Chapter(
                        book_id=book.id,
                        sequence=c_data.get("sequence", 1),
                        title_en=c_data["title"]
                    )
                    db.add(chapter)
                    await db.flush()
                
                topics_data = c_data.get("topics", [])
                for t_data in topics_data:
                    res = await db.execute(select(Topic).where(Topic.chapter_id == chapter.id, Topic.title_en == t_data["title"]))
                    topic = res.scalar_one_or_none()
                    if not topic:
                        topic = Topic(
                            chapter_id=chapter.id,
                            sequence=t_data.get("sequence", 1),
                            title_en=t_data["title"]
                        )
                        db.add(topic)
                        await db.flush()
                    
                    concepts_data = t_data.get("concepts", [])
                    for i, con_data in enumerate(concepts_data):
                        res = await db.execute(select(Concept).where(Concept.topic_id == topic.id, Concept.name_en == con_data["name"]))
                        concept = res.scalar_one_or_none()
                        if not concept:
                            concept = Concept(
                                topic_id=topic.id,
                                name_en=con_data["name"],
                                description=con_data.get("description", "")
                            )
                            db.add(concept)
                            await db.flush()
                        
                        lo_text = con_data.get("learning_outcome")
                        if lo_text:
                            res = await db.execute(select(LearningOutcome).where(LearningOutcome.concept_id == concept.id, LearningOutcome.description_en == lo_text))
                            lo = res.scalar_one_or_none()
                            if not lo:
                                lo = LearningOutcome(
                                    concept_id=concept.id,
                                    description_en=lo_text
                                )
                                db.add(lo)
                                await db.flush()
        
        await db.commit()
        print("Import successfully finished!")

if __name__ == "__main__":
    asyncio.run(import_json())
