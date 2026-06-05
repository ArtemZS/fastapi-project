from pydantic import BaseModel, Field, ConfigDict, EmailStr


class UserCreate(BaseModel):
    email: EmailStr = Field(description="Email пользователя")
    password: str = Field(min_length=8, description="Пароль (минимум 8 символом)")
    role: str = Field(default="buyer", pattern="^(buyer|seller|admin)$", description="Роль: 'buyer' или 'seller' или 'admin'")


class User(BaseModel):
    id: int
    email: EmailStr
    is_active: bool
    role: str
    
    model_config = ConfigDict(from_attributes=True)