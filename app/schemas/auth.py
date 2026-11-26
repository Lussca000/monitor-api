from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserBase(BaseModel):
    username: str = Field(min_length=3, max_length=50)


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class LoginRequest(BaseModel):
    username: str
    password: str
