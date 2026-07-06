from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from typing import List

from app.core.deps import get_db, get_current_user
from app.db.models.auth import User
from app.db.models.mcq_engine import (
    MCQEngineCurriculum, MCQETextbook, MCQEGenerationJob
)
from app.schemas.mcq_engine import (
    CurriculumCreate, CurriculumResponse, TextbookCreate, TextbookResponse, GenerationJobCreate, GenerationJobResponse
)

router = APIRouter()

@router.post("/curriculum", response_model=CurriculumResponse)
async def upload_curriculum(
    curr_in: CurriculumCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    curriculum = MCQEngineCurriculum(
        class_name=curr_in.class_name,
        subject_id=curr_in.subject_id
    )
    db.add(curriculum)
    await db.commit()
    await db.refresh(curriculum)
    return {"id": curriculum.id, "message": "Curriculum uploaded successfully"}

@router.post("/textbook", response_model=TextbookResponse)
async def upload_textbook(
    class_name: str = Form(...),
    subject_id: int = Form(...),
    curriculum_id: int = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    import os
    import shutil
    import uuid
    
    os.makedirs("uploads/textbooks", exist_ok=True)
    file_path = f"uploads/textbooks/{uuid.uuid4()}_{file.filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    textbook = MCQETextbook(
        class_name=class_name,
        subject_id=subject_id,
        curriculum_id=curriculum_id,
        book_name=file.filename,
        file_path=file_path
    )
    db.add(textbook)
    await db.commit()
    await db.refresh(textbook)
    return {
        "id": textbook.id, 
        "message": "Textbook uploaded successfully",
        "class_name": textbook.class_name,
        "subject_id": textbook.subject_id,
        "curriculum_id": textbook.curriculum_id,
        "book_name": textbook.book_name
    }

from app.services.mcq_engine_service import run_generation_job

@router.post("/generate", response_model=GenerationJobResponse)
async def trigger_generation(
    job_in: GenerationJobCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    job = MCQEGenerationJob(
        teacher_id=current_user.id,
        class_name=job_in.class_name,
        subject_id=job_in.subject_id,
        textbook_id=job_in.textbook_id,
        language=job_in.language.value,
        status="pending"
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    
    # We should NOT pass the AsyncSession to the background task directly because the current request's session will close.
    # Instead, the background task should create its own session. We'll pass the job_id.
    background_tasks.add_task(run_generation_job, job.id)
    
    return job

from fastapi.responses import Response

@router.get("/papers/{job_id}/download")
async def download_papers(job_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.services.pdf_generator import generate_papers_zip
    
    zip_bytes = await generate_papers_zip(db, job_id)
    return Response(
        content=zip_bytes,
        media_type="application/x-custom-zip"
    )

@router.post("/omr/upload")
async def upload_omr(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from app.services.omr_scanner import evaluate_omr_sheet
    import os, shutil, uuid
    
    os.makedirs("uploads/omr", exist_ok=True)
    file_path = f"uploads/omr/{uuid.uuid4()}_{file.filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        student_result_id = await evaluate_omr_sheet(db, file_path)
        return {"message": "OMR processed successfully", "student_result_id": student_result_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/student-results/{student_result_id}/marked-sheet")
async def download_marked_sheet(student_result_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.services.pdf_generator import generate_marked_answer_sheet
    
    try:
        pdf_bytes = await generate_marked_answer_sheet(db, student_result_id)
        return Response(
            content=pdf_bytes,
            media_type="application/x-custom-pdf"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/student-results/{student_result_id}/concept-analysis")
async def download_concept_analysis(student_result_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.services.pdf_generator import generate_concept_analysis_report
    
    try:
        pdf_bytes = await generate_concept_analysis_report(db, student_result_id)
        return Response(
            content=pdf_bytes,
            media_type="application/x-custom-pdf"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
