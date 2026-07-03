from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class SubjectCreate(BaseModel):
    name_en: str
    name_hi: Optional[str] = None
    name_gu: Optional[str] = None
    code: Optional[str] = None
    grade: Optional[int] = None


class SubjectResponse(BaseModel):
    id: int
    name_en: str
    name_hi: Optional[str] = None
    name_gu: Optional[str] = None
    code: Optional[str] = None
    grade: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BookCreate(BaseModel):
    school_id: int
    subject_id: int
    grade: int
    title: str
    file_path: str
    source_type: Optional[str] = None
    uploaded_by: Optional[int] = None


class BookResponse(BaseModel):
    id: int
    school_id: int
    subject_id: int
    grade: int
    title: str
    file_path: str
    source_type: Optional[str] = None
    processing_status: str
    processing_error: Optional[str] = None
    uploaded_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChapterCreate(BaseModel):
    book_id: int
    unit_name: Optional[str] = None
    sequence: Optional[int] = None
    title_en: str
    title_hi: Optional[str] = None
    title_gu: Optional[str] = None


class ChapterResponse(BaseModel):
    id: int
    book_id: int
    unit_name: Optional[str] = None
    sequence: Optional[int] = None
    title_en: str
    title_hi: Optional[str] = None
    title_gu: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TopicCreate(BaseModel):
    chapter_id: int
    sequence: Optional[int] = None
    title_en: str
    title_hi: Optional[str] = None
    title_gu: Optional[str] = None


class TopicResponse(BaseModel):
    id: int
    chapter_id: int
    sequence: Optional[int] = None
    title_en: str
    title_hi: Optional[str] = None
    title_gu: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConceptCreate(BaseModel):
    topic_id: int
    name_en: str
    name_hi: Optional[str] = None
    name_gu: Optional[str] = None
    description: Optional[str] = None
    extracted_by: str = "ai"


class ConceptResponse(BaseModel):
    id: int
    topic_id: int
    name_en: str
    name_hi: Optional[str] = None
    name_gu: Optional[str] = None
    description: Optional[str] = None
    extracted_by: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LearningOutcomeCreate(BaseModel):
    concept_id: int
    code: Optional[str] = None
    description_en: str
    description_hi: Optional[str] = None
    description_gu: Optional[str] = None


class LearningOutcomeResponse(BaseModel):
    id: int
    concept_id: int
    code: Optional[str] = None
    description_en: str
    description_hi: Optional[str] = None
    description_gu: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CompetencyCreate(BaseModel):
    name_en: str
    name_hi: Optional[str] = None
    name_gu: Optional[str] = None
    nas_parakh_code: Optional[str] = None
    description: Optional[str] = None


class CompetencyResponse(BaseModel):
    id: int
    name_en: str
    name_hi: Optional[str] = None
    name_gu: Optional[str] = None
    nas_parakh_code: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class KnowledgeChunkCreate(BaseModel):
    book_id: int
    chapter_id: Optional[int] = None
    chunk_text: str
    chunk_index: Optional[int] = None
    chroma_vector_id: Optional[str] = None
    token_count: Optional[int] = None


class KnowledgeChunkResponse(BaseModel):
    id: int
    book_id: int
    chapter_id: Optional[int] = None
    chunk_text: str
    chunk_index: Optional[int] = None
    chroma_vector_id: Optional[str] = None
    token_count: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
