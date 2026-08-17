from pydantic import BaseModel
from typing import Optional, List, Dict
from enum import Enum


class LanguageEnum(str, Enum):
    english = "english"
    hindi = "hindi"
    gujarati = "gujarati"


class CurriculumCreate(BaseModel):
    class_name: str
    subject_id: int


class CurriculumResponse(BaseModel):
    id: int
    message: str


class TextbookCreate(BaseModel):
    class_name: str
    subject_id: int
    curriculum_id: int
    book_name: str


class TextbookResponse(BaseModel):
    id: int
    message: str
    class_name: str
    subject_id: int
    curriculum_id: int
    book_name: str


class GenerationJobCreate(BaseModel):
    class_name: str
    subject_id: int
    textbook_id: int
    language: LanguageEnum


class OMRUploadRequest(BaseModel):
    # Depending on how the file is uploaded, normally this is a File/UploadFile parameter in FastAPI
    # This schema is just a placeholder if needed
    pass


class GenerationJobResponse(BaseModel):
    id: int
    class_name: str
    subject_id: int
    textbook_id: int
    language: str
    status: str

    class Config:
        from_attributes = True
