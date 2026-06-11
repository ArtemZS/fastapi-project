from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi.security import OAuth2PasswordRequestForm

from app.db_depends import get_async_db
from app.models.users import User as UserModel
from app.schemas.users import User as UserSchema, UserCreate
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, validate_token, CredentialsException
from app.schemas.auth import TokenResponse, RefreshTokenRequest, RefreshTokenResponse
from app.services_for_routers.auth import AuthService
from app.services_for_routers.users import UserService

router = APIRouter(
    prefix="/users",
    tags=["users"],
    deprecated=True
)

router_v2 = APIRouter(
    prefix="/v2/users",
    tags=["v2/users"]
)

@router.post("/", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_async_db)):
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

#? используем POST
@router.post("/token", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_async_db)):
    """
    Аутентифицирует пользователя и возвращает access_token и refresh_token.
    """
    user = await db.scalar(
        select(UserModel).where(
            UserModel.email == form_data.username,
            UserModel.is_active == True
        )
    )
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise CredentialsException("Incorrect email or password")

    access_token = create_access_token(data={"sub": user.email, "role": user.role, "id": user.id})
    refresh_token = create_refresh_token(data={"sub": user.email, "id": user.id})
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


#! реализовать ротацию рефреш-токенов в будущем, сейчас просто выдаём новый access_token по валидному refresh_token
@router.post("/refresh-token", response_model=RefreshTokenResponse, status_code=status.HTTP_200_OK)
async def refresh_token(payload: RefreshTokenRequest, db: AsyncSession = Depends(get_async_db)):
    """
    Обновляет access_token с помощью refresh_token.
    """
    email = validate_token(payload.refresh_token, expected_type="refresh")
    user = await db.scalar(
        select(UserModel).where(
            UserModel.email == email,
            UserModel.is_active == True
        )
    )
    if user is None:
        raise CredentialsException("User not found")
    
    access_token = create_access_token(data={"sub": user.email, "role": user.role, "id": user.id})
    return RefreshTokenResponse(
        access_token=access_token,
        token_type="bearer"
    )


@router_v2.post("/", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
async def create_user_v2(user: UserCreate, db: AsyncSession = Depends(get_async_db)):
    """
    Регистрирует нового пользователя с ролью 'buyer' или 'seller' или "admin".
    """
    return await UserService.create_user(user, db)
    
@router_v2.post("/token", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_async_db)):
    """
    Аутентифицирует пользователя и возвращает access_token и refresh_token.
    """   
    return await AuthService.login(form_data, db)

@router_v2.post("/refresh-token", response_model=RefreshTokenResponse, status_code=status.HTTP_200_OK)
async def refresh_token(payload: RefreshTokenRequest, db: AsyncSession = Depends(get_async_db)):
    """
    Обновляет access_token с помощью refresh_token.
    """
    return await AuthService.refresh_token(payload, db)