from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import OAuth2PasswordRequestForm

from app.core.db_depends import get_async_db
from app.schemas.users import User as UserSchema, UserCreate
from app.schemas.auth import TokenResponse, RefreshTokenRequest, RefreshTokenResponse
from app.services.auth import AuthService
from app.services.users import UserService

router = APIRouter(
    prefix="/users",
    tags=["/users"]
)

@router.post("/", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_async_db)):
    """
    Регистрирует нового пользователя с ролью 'buyer' или 'seller' или "admin".
    """
    return await UserService.create_user(user, db)
    
@router.post("/token", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_async_db)):
    """
    Аутентифицирует пользователя и возвращает access_token и refresh_token.
    """   
    return await AuthService.login(form_data, db)

@router.post("/refresh-token", response_model=RefreshTokenResponse, status_code=status.HTTP_200_OK)
async def refresh_token(payload: RefreshTokenRequest, db: AsyncSession = Depends(get_async_db)):
    """
    Обновляет access_token с помощью refresh_token.
    """
    return await AuthService.refresh_token(payload, db)