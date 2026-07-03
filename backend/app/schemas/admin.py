from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ReportCreate(BaseModel):
    school_id: int
    report_type: Optional[str] = None
    reference_id: Optional[int] = None
    file_path: Optional[str] = None
    generated_by: Optional[int] = None


class ReportResponse(BaseModel):
    id: int
    school_id: int
    report_type: Optional[str] = None
    reference_id: Optional[int] = None
    file_path: Optional[str] = None
    generated_at: Optional[datetime] = None
    generated_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    school_id: Optional[int] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[int] = None
    metadata: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class BackupCreate(BaseModel):
    school_id: int
    file_path: Optional[str] = None
    backup_type: Optional[str] = None
    size_bytes: Optional[int] = None
    created_by: Optional[int] = None


class BackupResponse(BaseModel):
    id: int
    school_id: int
    file_path: Optional[str] = None
    backup_type: Optional[str] = None
    size_bytes: Optional[int] = None
    created_at: datetime
    created_by: Optional[int] = None

    class Config:
        from_attributes = True


class SettingCreate(BaseModel):
    school_id: Optional[int] = None
    key: str
    value: Optional[str] = None


class SettingResponse(BaseModel):
    id: int
    school_id: Optional[int] = None
    key: str
    value: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
