"""
Application configuration management.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings."""

    # API Settings
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "FastAPI Production Template"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "Production-ready FastAPI application with clean architecture"

    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # CORS
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # Git OAuth Client IDs (optional - required for OAuth to work)
    GITHUB_CLIENT_ID: str | None = None
    GITLAB_CLIENT_ID: str | None = None
    GITEA_CLIENT_ID: str | None = None

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
