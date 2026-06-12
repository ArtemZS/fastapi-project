from pydantic import BaseModel, Field, ConfigDict, EmailStr
from enum import Enum


class UserRole(Enum):
    buyer = "buyer"
    seller = "seller"
    admin = "admin"


class UserCreate(BaseModel):
    email: EmailStr = Field(description="Email пользователя")
    password: str = Field(min_length=8, description="Пароль (минимум 8 символом)")
    role: UserRole = Field(default=UserRole.buyer, description="Роль пользователя: buyer, seller или admin")


class User(BaseModel):
    id: int
    email: EmailStr
    is_active: bool
    role: UserRole
    
    model_config = ConfigDict(from_attributes=True)