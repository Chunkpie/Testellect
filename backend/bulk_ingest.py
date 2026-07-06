import os
import re
import asyncio
import sys

# Add backend to path so we can import app modules
sys.path.append(os.path.join(os.path.dirname(__file__), "app"))

from app.core.database import async_session_factory
from app.db.models.curriculum import Book
from app.services.ai_service import AiService
import shutil

CURRICULUM_DIR = "/app/Curriculum"
UPLOAD_DIR = "/app/uploads"

SUBJECT_MAP = {
    1: r"sci|env.*sci", # Science
    2: r"math", # Mathematics
    3: r"env|our.*world", # Environmental Studies
    4: r"eng|marigold|honeysuckle|first flight|footprints|beehive|moments|dolphin|pact|santoor|mridang", # English
    5: r"guj", # Gujarati
    6: r"hin", # Hindi
    7: r"social|soc|history|geo|eco|civics", # Social Science
    8: r"comp", # Computer Science
    9: r"sanskrit|sanskrut", # Sanskrit
}

def get_grade(filename: str) -> int:
    match = re.search(r"std[-_ ]*(\d+)", filename, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return 1 # Default

def get_subject_id(filename: str) -> int:
    name_lower = filename.lower()
    for subject_id, pattern in SUBJECT_MAP.items():
        if re.search(pattern, name_lower):
            return subject_id
    return 4 # Default to English if unknown

async def main():
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    pdfs = []
    for root, _, files in os.walk(CURRICULUM_DIR):
        for f in files:
            if f.lower().endswith(".pdf"):
                pdfs.append(os.path.join(root, f))
    
    print(f"Found {len(pdfs)} PDFs to ingest.")
    
    for idx, pdf_path in enumerate(pdfs):
        filename = os.path.basename(pdf_path)
        grade = get_grade(filename)
        subject_id = get_subject_id(filename)
        
        print(f"\n[{idx+1}/{len(pdfs)}] Ingesting: {filename}")
        print(f"   -> Detected Grade: {grade}, Subject ID: {subject_id}")
        
        # Hard filter for English books only
        lower_name = filename.lower()
        if "gujarati" in lower_name or "hindi" in lower_name or "sanskrut" in lower_name or "sanskrit" in lower_name or "farsi" in lower_name or "black-buck" in lower_name or "sarvangi" in lower_name:
            print(f"   -> SKIPPING: Non-English or corrupted book based on filename filter.")
            continue
            
        async with async_session_factory() as session:
            # Check if already exists
            existing = await session.execute(Book.__table__.select().where(Book.title == filename.replace(".pdf", "")))
            if existing.fetchone():
                print(f"   -> SKIPPING: Book already exists in database.")
                continue
                
            # Copy file to uploads dir
            safe_name = f"bulk_{idx}_{filename}"
            dest_path = os.path.join(UPLOAD_DIR, safe_name)
            shutil.copy2(pdf_path, dest_path)
            
            # Create Book record
            book = Book(
                school_id=1,
                subject_id=subject_id,
                grade=grade,
                title=filename.replace(".pdf", ""),
                file_path=dest_path,
                source_type="pdf",
                processing_status="processing",
                uploaded_by=None
            )
            session.add(book)
            await session.commit()
            await session.refresh(book)
            
            print(f"   -> Book ID {book.id} created. Starting AI Analysis in subprocess...")
            import subprocess
            try:
                # Spawn as a separate process so memory is strictly freed after it completes
                result = subprocess.run(
                    ["python", "/app/analyze_single.py", str(book.id)],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    print(f"   -> Successfully analyzed Book ID {book.id}")
                    # Print tail of output just to confirm
                    print(result.stdout.strip().split('\n')[-3:])
                else:
                    print(f"   -> ERROR analyzing Book ID {book.id}. Return code: {result.returncode}")
                    print(f"   -> STDERR: {result.stderr}")
                    # Since it failed, we can optionally rollback the status here if we wanted to
                    
            except Exception as e:
                print(f"   -> FATAL ERROR spawning subprocess for Book ID {book.id}: {e}")
                
        # Sleep between books to strictly enforce rate limits across the huge run
        print("   -> Sleeping for 15 seconds to reset Groq RPM buckets...")
        await asyncio.sleep(15)

if __name__ == "__main__":
    asyncio.run(main())
