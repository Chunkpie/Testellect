from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class BlueprintCreate(BaseModel):
    school_id: int
    created_by: Optional[int] = None
    name: str
    grade: int
    subject_id: int
    chapter_ids: Optional[str] = None
    total_questions: int
    total_marks: float
    difficulty_distribution: Optional[str] = None
    bloom_distribution: Optional[str] = None
    competency_distribution: Optional[str] = None
    duration_minutes: Optional[int] = None


class BlueprintResponse(BaseModel):
    id: int
    school_id: int
    created_by: Optional[int] = None
    name: str
    grade: int
    subject_id: int
    chapter_ids: Optional[str] = None
    total_questions: int
    total_marks: float
    difficulty_distribution: Optional[str] = None
    bloom_distribution: Optional[str] = None
    competency_distribution: Optional[str] = None
    duration_minutes: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PaperCreate(BaseModel):
    blueprint_id: int
    variant_label: str
    generated_by: Optional[int] = None


class PaperResponse(BaseModel):
    id: int
    blueprint_id: int
    variant_label: str
    pdf_file_path: Optional[str] = None
    generated_at: Optional[datetime] = None
    generated_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PaperQuestionSchema(BaseModel):
    paper_id: int
    question_id: int
    sequence: int
    option_order: Optional[str] = None
