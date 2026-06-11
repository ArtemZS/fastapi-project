from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    refresh_token_expire_days: int
    
    yookassa_shop_id: int
    yookassa_secret_key: str
    
    db_username: str
    db_password: str
    db_host: str
    db_port: int
    db_name: str

    # Настройки для чтения .env
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False  
    )

settings = Settings()