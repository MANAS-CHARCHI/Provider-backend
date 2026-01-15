from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import datetime
from typing import Optional

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    model_config = ConfigDict(from_attributes=True)

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    location: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    twitter: Optional[str] = None
    website: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class UserResponse(BaseModel):
    email: EmailStr
    full_name: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime | None    
    role: str
    model_config = ConfigDict(from_attributes=True)

class UserProfileResponse(BaseModel):
    email: EmailStr
    full_name: str | None
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime | None
    location: str | None
    linkedin: str | None
    github: str | None
    twitter: str | None
    website: str | None
    model_config = ConfigDict(from_attributes=True)

class UserReviewBody(BaseModel):
    review: str
    consent: bool

class PublicUserProfile(BaseModel):
    full_name: str | None
    linkedin: str | None
    github: str | None
    twitter: str | None
    website: str | None

    model_config = ConfigDict(from_attributes=True)

class UserReviewResponse(BaseModel):
    reviewer: PublicUserProfile
    review_id: int
    review: str
    consent: bool
    model_config = ConfigDict(from_attributes=True)

class UserLogin(BaseModel):
    email: EmailStr
    password: str
    model_config = ConfigDict(from_attributes=True)

class UserLoginResponse(BaseModel):
    email: EmailStr
    model_config = ConfigDict(from_attributes=True)

class InvitationCreate(BaseModel):
    email: EmailStr
    role: str
    model_config = ConfigDict(from_attributes=True)
