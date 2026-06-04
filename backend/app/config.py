from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    ENV: Literal["development", "testing", "production"] = "development"
    DEBUG: bool = True

    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/device_manager"

    API_TITLE: str = "Device Manager API"
    API_VERSION: str = "1.0.0"

    SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24

    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
