from app.models.users import User as UserModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from app.auth import verify_password, create_access_token, create_refresh_token, CredentialsException, validate_token
from app.schemas.auth import TokenResponse, RefreshTokenRequest, RefreshTokenResponse


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/token")

class AuthService:
    @staticmethod
    async def login(
        form_data: OAuth2PasswordRequestForm,
        db: AsyncSession
    ):
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
            refresh_token=refresh_token
        )
        
    @staticmethod
    async def refresh_token(
        payload: RefreshTokenRequest,
        db: AsyncSession
    ):
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