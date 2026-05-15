from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

"""
BaseModel
    ├── UserBase           (基础用户信息)
    │       ├── UserCreate (创建用户)
    │       └── UserResponse (响应用户信息)
    │
    ├── UserUpdate         (更新用户)
    ├── LoginRequest       (登录请求)
    └── TokenResponse      (登录响应)
"""


class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    role: str = "student"


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None


class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
