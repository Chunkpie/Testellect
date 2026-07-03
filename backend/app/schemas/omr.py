from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class OMRSheetCreate(BaseModel):
    paper_id: int
    student_id: Optional[int] = None
    assessment_id: int
    qr_payload: Optional[str] = None
    barcode_payload: Optional[str] = None
    sheet_pdf_path: Optional[str] = None
    status: str = "generated"


class OMRSheetResponse(BaseModel):
    id: int
    paper_id: int
    student_id: Optional[int] = None
    assessment_id: int
    qr_payload: Optional[str] = None
    barcode_payload: Optional[str] = None
    sheet_pdf_path: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OMRResultCreate(BaseModel):
    omr_sheet_id: int
    scanned_image_path: Optional[str] = None
    detected_answers: Optional[str] = None
    raw_score: Optional[float] = None
    max_score: Optional[float] = None
    scan_confidence: Optional[float] = None
    needs_manual_review: bool = False
    scanned_by: Optional[int] = None
    scanned_at: Optional[datetime] = None


class OMRResultResponse(BaseModel):
    id: int
    omr_sheet_id: int
    scanned_image_path: Optional[str] = None
    detected_answers: Optional[str] = None
    raw_score: Optional[float] = None
    max_score: Optional[float] = None
    scan_confidence: Optional[float] = None
    needs_manual_review: bool
    scanned_by: Optional[int] = None
    scanned_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
