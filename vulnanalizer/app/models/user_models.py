"""
Pydantic модели для пользователей
"""
from typing import Optional
from pydantic import BaseModel


class UserCreate(BaseModel):
    username: str
    email: Optional[str] = None
    password: str
    is_admin: bool = False


class UserUpdate(BaseModel):
    username: str
    email: Optional[str] = None
    is_active: bool
    is_admin: bool


class PasswordUpdate(BaseModel):
    password: str
