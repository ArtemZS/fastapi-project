from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db_depends import get_async_db
from app.models.users import User as UserModel
from app.core.config import settings

# Создаём контекст для хеширования с использованием bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes
REFRESH_TOKEN_EXPIRE_DAYS = settings.refresh_token_expire_days

# Путь должен указывать на эндпоинт, который выдаёт токены (обычно это /users/token)
# Сюда прокидывается Request из которого достается токен из заголовка Authorization
# Depends(RoleChecker("admin") <- Depends(get_current_user) <- Depends(oauth2_scheme)) 
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/token")


class CredentialsException(HTTPException):
    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class RoleException(HTTPException):
    def __init__(self, allowed_roles: str | list[str] = "buyer"):
        if isinstance(allowed_roles, str):
            roles_list = [allowed_roles]
        else:
            roles_list = allowed_roles

        message = f"Only {', '.join(roles_list)} can perform this action"
        
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=message,
        )

def hash_password(password: str) -> str:
    """Преобразует пароль в хеш с использованием bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверяет, соответствует ли введённый пароль сохранённому хешу."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    """Создаёт JWT с payload (sub, role, id, exp, type)."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(data: dict) -> str:
    """Создаёт рефреш-токен с длительным сроком действия."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def validate_token(token: str, expected_type: str = "access") -> str:
    """
    Декодирует JWT, проверяет его валидность и тип.
    Возвращает email из payload, если токен валиден.
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        email: str = payload.get("sub")
        
        # Сразу проверяем и наличие email, и соответствие типа токена
        if email is None or payload.get("type") != expected_type:
            raise CredentialsException("Invalid token credentials")
            
        return email
        
    except jwt.ExpiredSignatureError:
        raise CredentialsException("Token has expired")
    except jwt.PyJWTError:
        raise CredentialsException("Invalid token")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_async_db)
) -> UserModel:
    """Возвращает активного пользователя из базы данных на основе токена."""
    email = validate_token(token)
    user = await db.scalar(
        select(UserModel).where(UserModel.email == email, UserModel.is_active == True)
    )
    if user is None:
        raise CredentialsException("User not found or inactive")
    return user


class RoleChecker:
    """
    Зависимость для проверки роли пользователя. Принимает одну или несколько разрешённых ролей и проверяет, 
    соответствует ли роль текущего пользователя одной из них. 
    Если нет, выбрасывает исключение с кодом 403.
    """
    
    def __init__(self, allowed_roles: str | list[str] = "buyer"):
        # Можем принимать как одну роль "admin", так и список ["admin", "seller"]
        if isinstance(allowed_roles, str):
            self.allowed_roles = [allowed_roles]
        else:
            self.allowed_roles = allowed_roles

    async def __call__(self, current_user: UserModel = Depends(get_current_user)) -> UserModel:
        if current_user.role not in self.allowed_roles:
            # Выбрасываем исключение, если роли пользователя нет в списке разрешенных
            # Передаем в detail ожидаемую роль
            raise RoleException(allowed_roles=self.allowed_roles)
        return current_user