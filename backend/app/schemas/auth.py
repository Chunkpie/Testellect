from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    school_id: Optional[int] = None
    district_id: Optional[int] = None
    full_name: str
    email: str
    phone: Optional[str] = None
    password: str
    role: str = "teacher"
    preferred_language: str = "en"


class UserResponse(BaseModel):
    id: int
    school_id: Optional[int] = None
    district_id: Optional[int] = None
    full_name: str
    email: str
    phone: Optional[str] = None
    role: str
    preferred_language: str
    is_active: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    preferred_language: Optional[str] = None
    is_active: Optional[bool] = None
