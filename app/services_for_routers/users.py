from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.users import User as UserModel
from app.schemas.users import UserCreate
from app.auth import hash_password
from fastapi import HTTPException, status

class UserService:
    @staticmethod
    async def create_user(
        user: UserCreate,
        db: AsyncSession
    ):
        """
        Регистрирует нового пользователя с ролью 'buyer' или 'seller' или "admin".
        """
        # Проверка уникальности email
        result = await db.scalar(select(UserModel).where(UserModel.email == user.email))
        if result:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="Email already registered")

        # Создание объекта пользователя с хешированным паролем
        db_user = UserModel(
            email=user.email,
            hashed_password=hash_password(user.password),
            role=user.role
        )

        # Добавление в сессию и сохранение в базе
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        return db_user