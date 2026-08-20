import asyncio
import json
import os
import sys

# Ensure backend directory is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import async_session_factory
from sqlalchemy import select
from app.db.models import (
    Subject,
    Book,
    Chapter,
    Topic,
    Concept,
    LearningOutcome
)

async def import_curriculum():
    base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Curriculum")
    if not os.path.exists(base_dir):
        print(f"Curriculum directory not found at {base_dir}")
        return

    async with async_session_factory() as db:
        for class_folder in os.listdir(base_dir):
            class_path = os.path.join(base_dir, class_folder)
            if not os.path.isdir(class_path):
                continue
            
            # e.g. "Class 10" -> grade 10
            grade_str = class_folder.replace("Class ", "").strip()
            if not grade_str.isdigit():
                continue
            grade = int(grade_str)

            for subject_folder in os.listdir(class_path):
                subject_path = os.path.join(class_path, subject_folder)
                if not os.path.isdir(subject_path):
                    continue
                
                subject_name = subject_folder.strip()

                # Get or create subject
                res = await db.execute(select(Subject).where(Subject.name_en == subject_name))
                subject = res.scalar_one_or_none()
                if not subject:
                    subject = Subject(name_en=subject_name, grade=grade)
                    db.add(subject)
                    await db.flush()
                
                # Get or create book
                book_title = f"{subject_name} Grade {grade}"
                res = await db.execute(select(Book).where(Book.title == book_title))
                book = res.scalar_one_or_none()
                if not book:
                    book = Book(
                        subject_id=subject.id,
                        grade=grade,
                        title=book_title,
                        file_path="imported_from_json",
                        source_type="json",
                        processing_status="completed"
                    )
                    db.add(book)
                    await db.flush()
                
                for file_name in os.listdir(subject_path):
                    if not file_name.endswith(".json"):
                        continue
                    
                    file_path = os.path.join(subject_path, file_name)
                    with open(file_path, "r", encoding="utf-8") as f:
                        try:
                            data = json.load(f)
                        except json.JSONDecodeError:
                            print(f"Failed to parse {file_path}")
                            continue

                        chapter_seq = data.get("sequence", 1)
                        chapter_title = data.get("title", file_name.replace(".json", ""))

                        chapter = Chapter(
                            book_id=book.id,
                            sequence=chapter_seq,
                            title_en=chapter_title
                        )
                        db.add(chapter)
                        await db.flush()

                        for topic_data in data.get("topics", []):
                            topic = Topic(
                                chapter_id=chapter.id,
                                sequence=topic_data.get("sequence", 1),
                                title_en=topic_data.get("title", "Untitled Topic")
                            )
                            db.add(topic)
                            await db.flush()

                            for concept_data in topic_data.get("concepts", []):
                                concept = Concept(
                                    topic_id=topic.id,
                                    name_en=concept_data.get("name", "Untitled Concept"),
                                    description=concept_data.get("description", ""),
                                    concept_title=concept_data.get("name", "Untitled Concept"),
                                    concept_summary_text=concept_data.get("description", "")
                                )
                                db.add(concept)
                                await db.flush()

                                lo_text = concept_data.get("learning_outcome")
                                if lo_text:
                                    lo = LearningOutcome(
                                        concept_id=concept.id,
                                        description_en=lo_text
                                    )
                                    db.add(lo)
                                    await db.flush()

        await db.commit()
        print("Curriculum import completed successfully.")

if __name__ == "__main__":
    asyncio.run(import_curriculum())
