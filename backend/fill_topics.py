import asyncio
import json
import os
import sys

# Setup imports the same way as fast_extract2
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from sqlalchemy import text

sys.path.append("/app")
from app.models import Book, Chapter, Topic, Concept
from app.core.config import settings
import httpx

engine = create_async_engine(settings.DATABASE_URL)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

async def generate_topics_for_chapter(chapter_title, book_title):
    prompt = f"""
You are an expert curriculum designer. Given the subject "{book_title}" and chapter title "{chapter_title}", generate a list of topics and concepts.
Return ONLY raw valid JSON (no markdown formatting, no ```json tags).

Use this EXACT JSON format:
{{
  "topics": [
    {{
      "sequence": 1,
      "title": "Topic Name",
      "concepts": [
        {{
          "name": "Concept Name",
          "description": "Concept explanation.",
          "learning_outcome": "Students will be able to..."
        }}
      ]
    }}
  ]
}}

Generate 2-4 topics, each with 2-3 concepts. Make them highly accurate and suitable for Grade 5 level.
"""
    
    payload = {
        "model": "llama3.2",
        "prompt": prompt,
        "format": "json",
        "stream": False
    }
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post("http://parakh-ollama:11434/api/generate", json=payload)
        response.raise_for_status()
        content = response.json()["response"]
        content = content.replace("```json", "").replace("```", "").strip()
        return json.loads(content)

async def main():
    async with async_session() as session:
        # Get all chapters with 0 topics
        result = await session.execute(text("""
            SELECT c.id, c.title_en, b.title 
            FROM chapters c 
            JOIN books b ON c.book_id = b.id 
            WHERE NOT EXISTS (SELECT 1 FROM topics t WHERE t.chapter_id = c.id)
            ORDER BY c.id
        """))
        chapters = result.fetchall()
        
        print(f"Found {len(chapters)} chapters needing topics...")
        
        for ch_id, ch_title, bk_title in chapters:
            print(f"Generating for: {bk_title} - {ch_title}...")
            try:
                data = await generate_topics_for_chapter(ch_title, bk_title)
                
                # Insert topics
                for t_data in data.get("topics", []):
                    topic = Topic(
                        chapter_id=ch_id,
                        sequence=t_data.get("sequence", 1),
                        title_en=t_data.get("title", "Topic")
                    )
                    session.add(topic)
                    await session.flush()
                    
                    for c_data in t_data.get("concepts", []):
                        concept = Concept(
                            topic_id=topic.id,
                            name_en=c_data.get("name", "Concept"),
                            description_en=c_data.get("description", ""),
                            learning_outcome_en=c_data.get("learning_outcome", "")
                        )
                        session.add(concept)
                        
                await session.commit()
                print(f"  -> Successfully added topics and concepts!")
            except Exception as e:
                print(f"  -> Failed: {e}")
                await session.rollback()

if __name__ == "__main__":
    asyncio.run(main())
