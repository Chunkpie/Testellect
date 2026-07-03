from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class DistrictCreate(BaseModel):
    name: str
    state: str = "Gujarat"


class DistrictResponse(BaseModel):
    id: int
    name: str
    state: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SchoolCreate(BaseModel):
    name: str
    udise_code: Optional[str] = None
    district_id: Optional[int] = None
    address: Optional[str] = None
    board: str = "GSEB"
    medium: Optional[str] = None


class SchoolResponse(BaseModel):
    id: int
    name: str
    udise_code: Optional[str] = None
    district_id: Optional[int] = None
    address: Optional[str] = None
    board: str
    medium: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SchoolUpdate(BaseModel):
    name: Optional[str] = None
    udise_code: Optional[str] = None
    district_id: Optional[int] = None
    address: Optional[str] = None
    board: Optional[str] = None
    medium: Optional[str] = None
    is_active: Optional[bool] = None
