from pydantic import BaseModel

class TokenResponse(BaseModel):
    """Схема ответа при авторизации согласно стандарту OAuth2 с Refresh токеном."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    

class RefreshTokenRequest(BaseModel):
    """Схема запроса для обновления токена."""
    refresh_token: str


class RefreshTokenResponse(BaseModel):
    """Схема успешного ответа при обновлении access-токена."""
    access_token: str
    token_type: str = "bearer"    