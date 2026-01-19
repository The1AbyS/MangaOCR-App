from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime


class UserBase(SQLModel):
    email: str = Field(max_length=255, unique=True, index=True, nullable=False)
    username: str = Field(max_length=50, unique=True, index=True, nullable=False)
    is_active: bool = True

class Token(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    token: str = Field(max_length=1024, unique=True, index=True)
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)

class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str = Field(nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Для регистрации
class UserCreate(UserBase):
    password: str


# Для ответа (без пароля)
class UserRead(UserBase):
    id: int
    created_at: datetime


# Для внутреннего использования (с паролем)
class UserInDB(UserBase):
    hashed_password: str