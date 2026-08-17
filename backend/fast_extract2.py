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

# OpenRouter Configuration
OPENROUTER_API_KEY = "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"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "openai/gpt-4o-mini"

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

import base64

async def extract_images_for_vision(pdf_path, max_pages=12):
    # Render first 12 pages as images for Vision LLMs since these are scanned textbooks
    doc = fitz.open(pdf_path)
    image_parts = []
    for i in range(min(max_pages, len(doc))):
        page = doc[i]
        pix = page.get_pixmap(dpi=100) # Lower dpi to save bandwidth
        img_bytes = pix.tobytes("jpeg")
        base64_str = base64.b64encode(img_bytes).decode("utf-8")
        image_parts.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{base64_str}"
            }
        })
    return image_parts

def _extract_json(text: str) -> str | None:
    text = text.strip()
    if text.startswith("```json"): text = text[7:]
    if text.endswith("```"): text = text[:-3]
    text = text.strip()
    
    start_char, end_char = "{", "}"
    start = text.find(start_char)
    if start >= 0:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == start_char: depth += 1
            elif text[i] == end_char:
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
    return None

async def get_curriculum_from_openrouter(image_parts):
    async with httpx.AsyncClient(timeout=120.0) as client:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://gseb-parakh.local",
            "X-Title": "GSEB Parakh"
        }
        
        # Combine text prompt and image parts
        content = [{"type": "text", "text": prompt_template}]
        content.extend(image_parts)
        
        payload = {
            "model": MODEL,
            "messages": [{"role": "user", "content": content}],
            "temperature": 0.1
        }
        res = await client.post(OPENROUTER_URL, headers=headers, json=payload)
        res.raise_for_status()
        data = res.json()
        raw_text = data["choices"][0]["message"]["content"]
        print(f"Raw response: {raw_text[:200]}...")
        
        json_str = _extract_json(raw_text) or raw_text
        return json.loads(json_str)

async def main():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        for b_info in BOOKS_TO_PROCESS:
            print(f"\nProcessing {b_info['title']}...")
            
            stmt = select(Book).where(Book.title == b_info['title'])
            res = await session.execute(stmt)
            book = res.scalar_one_or_none()
            
            pdf_path = os.path.join("/app/uploads", b_info['file'])
            if not os.path.exists(pdf_path):
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
                
            print(f"Extracting Table of Contents images from {pdf_path}...")
            image_parts = await extract_images_for_vision(pdf_path, max_pages=12)
            print(f"Extracted {len(image_parts)} page images.")
            
            print("Sending to OpenRouter (GPT-4o-Mini Vision) for rapid concept mapping...")
            try:
                curriculum_data = await get_curriculum_from_openrouter(image_parts)
            except httpx.HTTPStatusError as e:
                print(f"OpenRouter failed with {e.response.status_code}: {e.response.text}")
                continue
                
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
            print(f"Done processing {b_info['title']}! Status set to 'ready'.")

if __name__ == "__main__":
    asyncio.run(main())
