from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class QuestionOptionSchema(BaseModel):
    option_text_en: str
    option_text_hi: Optional[str] = None
    option_text_gu: Optional[str] = None
    is_correct: bool = False
    sequence: Optional[int] = None


class QuestionCreate(BaseModel):
    school_id: int
    concept_id: Optional[int] = None
    competency_id: Optional[int] = None
    learning_outcome_id: Optional[int] = None
    question_text_en: str
    question_text_hi: Optional[str] = None
    question_text_gu: Optional[str] = None
    question_type: str
    bloom_level: str
    difficulty: str
    marks: float
    estimated_time_seconds: Optional[int] = None
    explanation_en: Optional[str] = None
    explanation_hi: Optional[str] = None
    explanation_gu: Optional[str] = None
    options: list[QuestionOptionSchema] = []


class QuestionResponse(BaseModel):
    id: int
    school_id: int
    concept_id: Optional[int] = None
    competency_id: Optional[int] = None
    learning_outcome_id: Optional[int] = None
    question_text_en: str
    question_text_hi: Optional[str] = None
    question_text_gu: Optional[str] = None
    question_type: str
    bloom_level: str
    difficulty: str
    marks: float
    estimated_time_seconds: Optional[int] = None
    explanation_en: Optional[str] = None
    explanation_hi: Optional[str] = None
    explanation_gu: Optional[str] = None
    image_asset_id: Optional[int] = None
    image_url: Optional[str] = None
    confidence_score: Optional[float] = None
    duplicate_score: Optional[float] = None
    generated_by: str
    approval_status: str
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    is_deleted: bool
    options: list[QuestionOptionSchema] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class QuestionOptionResponse(BaseModel):
    id: int
    question_id: int
    option_text_en: str
    option_text_hi: Optional[str] = None
    option_text_gu: Optional[str] = None
    is_correct: bool
    sequence: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
