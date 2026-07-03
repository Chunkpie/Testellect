from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel


class AssessmentCreate(BaseModel):
    school_id: int
    blueprint_id: int
    class_id: int
    name: str
    scheduled_date: Optional[date] = None
    status: str = "scheduled"


class AssessmentResponse(BaseModel):
    id: int
    school_id: int
    blueprint_id: int
    class_id: int
    name: str
    scheduled_date: Optional[date] = None
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StudentResultCreate(BaseModel):
    assessment_id: int
    student_id: int
    omr_result_id: Optional[int] = None
    total_score: Optional[float] = None
    max_score: Optional[float] = None
    percentage: Optional[float] = None


class StudentResultResponse(BaseModel):
    id: int
    assessment_id: int
    student_id: int
    omr_result_id: Optional[int] = None
    total_score: Optional[float] = None
    max_score: Optional[float] = None
    percentage: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CompetencyResultSchema(BaseModel):
    student_result_id: int
    competency_id: int
    questions_attempted: Optional[int] = None
    questions_correct: Optional[int] = None
    mastery_level: Optional[str] = None
