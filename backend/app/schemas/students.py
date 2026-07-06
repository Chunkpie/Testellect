from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel


class ClassCreate(BaseModel):
    school_id: int
    grade: int
    section: Optional[str] = None
    academic_year: str
    class_teacher_id: Optional[int] = None


class ClassResponse(BaseModel):
    id: int
    school_id: int
    grade: int
    section: Optional[str] = None
    academic_year: str
    class_teacher_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StudentCreate(BaseModel):
    school_id: int
    class_id: int
    full_name: str
    roll_number: str
    gr_number: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None


class StudentResponse(BaseModel):
    id: int
    school_id: int
    class_id: int
    full_name: str
    roll_number: str
    class_name: Optional[str] = None
    school_name: Optional[str] = None
    gr_number: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StudentUpdate(BaseModel):
    full_name: Optional[str] = None
    roll_number: Optional[str] = None
    gr_number: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None
    is_active: Optional[bool] = None
