import asyncio
import os
import sys

sys.path.append("/app")
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.models import Chapter, Topic, Concept, LearningOutcome
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def main():
    async with async_session() as session:
        # Get all chapters from books 7 and 8 (English and EVS)
        result = await session.execute(text("""
            SELECT c.id, c.title_en
            FROM chapters c 
            WHERE c.book_id IN (7, 8)
        """))
        chapters = result.fetchall()
        
        print(f"Injecting additional topics for {len(chapters)} chapters...")
        
        for ch_id, ch_title in chapters:
            # We already have sequence 1 (or we can just query the max sequence)
            # To be safe, let's just query max sequence
            res = await session.execute(text(f"SELECT COALESCE(MAX(sequence), 0) FROM topics WHERE chapter_id = {ch_id}"))
            max_seq = res.scalar()
            
            additional_topics = [
                {
                    "title": f"Deep Dive into {ch_title}",
                    "concepts": [
                        {"name": f"Core Principles of {ch_title}", "description": f"Exploring the fundamental principles and underlying theory of {ch_title}.", "learning_outcome": f"Understand the core principles of {ch_title}."},
                        {"name": f"Practical Examples", "description": f"Real-world examples and case studies related to {ch_title}.", "learning_outcome": "Analyze practical examples."}
                    ]
                },
                {
                    "title": f"Applications and Analysis",
                    "concepts": [
                        {"name": "Analytical Thinking", "description": "Developing critical thinking skills.", "learning_outcome": "Apply analytical thinking to solve problems."},
                        {"name": f"Impact of {ch_title}", "description": f"Understanding the broader impact and significance of {ch_title}.", "learning_outcome": "Evaluate the broader impact."}
                    ]
                },
                {
                    "title": f"Summary and Review",
                    "concepts": [
                        {"name": "Key Takeaways", "description": "Summarizing the most important points from the chapter.", "learning_outcome": "Summarize key takeaways."},
                        {"name": "Practice Exercises", "description": "Applying knowledge through exercises and questions.", "learning_outcome": "Demonstrate understanding through practice."}
                    ]
                }
            ]
            
            for seq_offset, t_data in enumerate(additional_topics, 1):
                topic = Topic(chapter_id=ch_id, sequence=max_seq + seq_offset, title_en=t_data["title"])
                session.add(topic)
                await session.flush()
                
                for c_seq, c_data in enumerate(t_data["concepts"], 1):
                    concept = Concept(
                        topic_id=topic.id,
                        name_en=c_data["name"],
                        description=c_data["description"]
                    )
                    session.add(concept)
                    await session.flush()
                    
                    outcome = LearningOutcome(
                        concept_id=concept.id,
                        description_en=c_data["learning_outcome"]
                    )
                    session.add(outcome)
                    
            print(f"Added additional topics for {ch_title}")
        
        await session.commit()
        print("Done injecting all additional concepts!")

if __name__ == "__main__":
    asyncio.run(main())
