"""Application configuration management."""
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global application settings loaded from environment variables."""

    # Application
    app_name: str = Field(default="InSite Survey Backend")
    debug: bool = Field(default=False, alias="DEBUG")

    # MongoDB
    mongodb_uri: str = Field(default="mongodb://localhost:27017", alias="MONGODB_URI")
    mongodb_db: str = Field(default="insite_survey", alias="MONGODB_DB")

    # JWT Authentication
    jwt_secret_key: str = Field(default="change-me-in-production-use-strong-secret", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30000, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")

    # Password hashing
    bcrypt_rounds: int = Field(default=12, alias="BCRYPT_ROUNDS")

    # Application URLs (for QR codes and survey links)
    base_url: str = Field(default="http://localhost:3000", alias="BASE_URL")

    # Frontend URL (for email links like login button)
    # Falls back to base_url if not set
    frontend_url: str = Field(default="", alias="FRONTEND_URL")

    # Email Configuration (SMTP)
    smtp_host: str = Field(default="smtp.gmail.com", alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_user: str = Field(default="", alias="SMTP_USER")
    smtp_password: str = Field(default="", alias="SMTP_PASSWORD")
    smtp_from_email: str = Field(default="", alias="SMTP_FROM_EMAIL")
    smtp_from_name: str = Field(default="InSite Survey", alias="SMTP_FROM_NAME")
    smtp_use_tls: bool = Field(default=True, alias="SMTP_USE_TLS")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",
    )


@lru_cache
def get_settings() -> "Settings":
    """Return a cached settings instance."""

    return Settings()


settings = get_settings()
