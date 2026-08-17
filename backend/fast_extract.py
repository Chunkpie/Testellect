import asyncio
import os
import json
import httpx
import fitz  # PyMuPDF
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select

# We can import the models since we'll run this inside the backend container
import sys
sys.path.append("/app")
from app.models import Book, Chapter, Topic
from app.core.config import settings

# Get Gemini Key from environment or hardcode if needed
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AQ.Ab8RN6KQ36YtDNAMcNzpC1SyPxPaeFxrIqKnbZ6ghEsC3ZVrAQ")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

BOOKS_TO_PROCESS = [
    {
        "file": "Gujarat-Board-Class-5-English-First-Langauge-Textbook.pdf",
        "title": "Class 5 English First Language",
        "subject_id": 4
    },
    {
        "file": "GSEB-Std-5-Environment-Science-Textbook-2021-22English.pdf",
        "title": "Class 5 Environment Science",
        "subject_id": 3
    },
    {
        "file": "Gujarat-Board-Class-5-Maths-Textbook-in-English.pdf",
        "title": "Class 5 Maths",
        "subject_id": 2
    }
]

prompt_template = """
Extract the curriculum structure (chapters and topics) from the following textbook text.
Return ONLY valid JSON in this exact format, with no markdown formatting or extra text:
{
  "chapters": [
    {
      "sequence": 1,
      "title_en": "Chapter 1 Name",
      "topics": [
        {"sequence": 1, "title_en": "Topic 1"},
        {"sequence": 2, "title_en": "Topic 2"}
      ]
    }
  ]
}

Text:
"""

async def extract_text(pdf_path, max_pages=15):
    # Only read the first 15 pages which usually contains the Table of Contents!
    # Reading the whole 56MB book is unnecessary just for the syllabus structure.
    doc = fitz.open(pdf_path)
    text = ""
    for i in range(min(max_pages, len(doc))):
        text += doc[i].get_text() + "\n"
    return text

async def get_curriculum_from_gemini(text):
    async with httpx.AsyncClient(timeout=60.0) as client:
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt_template + text}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.1}
        }
        res = await client.post(GEMINI_URL, json=payload)
        res.raise_for_status()
        data = res.json()
        return json.loads(data["candidates"][0]["content"]["parts"][0]["text"])

async def main():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        for b_info in BOOKS_TO_PROCESS:
            print(f"Processing {b_info['title']}...")
            
            # Check if book exists in db, if not create it
            stmt = select(Book).where(Book.title == b_info['title'])
            res = await session.execute(stmt)
            book = res.scalar_one_or_none()
            
            pdf_path = os.path.join("/app/uploads", b_info['file'])
            if not os.path.exists(pdf_path):
                # Try finding it in uploads if hashed
                files = os.listdir("/app/uploads")
                for f in files:
                    if b_info['file'] in f:
                        pdf_path = os.path.join("/app/uploads", f)
                        break
            
            if not os.path.exists(pdf_path):
                print(f"File not found: {pdf_path}")
                continue
                
            if not book:
                book = Book(
                    title=b_info['title'],
                    grade=5,
                    subject_id=b_info['subject_id'],
                    file_path=pdf_path,
                    processing_status="uploaded"
                )
                session.add(book)
                await session.commit()
                await session.refresh(book)
                
            print(f"Extracting Table of Contents text from {pdf_path}...")
            text = await extract_text(pdf_path, max_pages=15)
            
            print("Sending to Gemini 1.5 Flash for rapid concept mapping...")
            try:
                curriculum_data = await get_curriculum_from_gemini(text)
            except Exception as e:
                print(f"Gemini failed: {e}")
                continue
                
            # Clear old chapters if any
            old_chapters = await session.execute(select(Chapter).where(Chapter.book_id == book.id))
            for ch in old_chapters.scalars().all():
                await session.delete(ch)
            await session.commit()
            
            print(f"Inserting {len(curriculum_data.get('chapters', []))} chapters into database...")
            for ch_data in curriculum_data.get('chapters', []):
                chapter = Chapter(
                    book_id=book.id,
                    title_en=ch_data['title_en'],
                    sequence=ch_data['sequence']
                )
                session.add(chapter)
                await session.commit()
                await session.refresh(chapter)
                
                for top_data in ch_data.get('topics', []):
                    topic = Topic(
                        chapter_id=chapter.id,
                        title_en=top_data['title_en'],
                        sequence=top_data['sequence']
                    )
                    session.add(topic)
                
            book.processing_status = "ready"
            await session.commit()
            print(f"Done processing {b_info['title']}! Status set to 'ready'.\n")

if __name__ == "__main__":
    asyncio.run(main())
