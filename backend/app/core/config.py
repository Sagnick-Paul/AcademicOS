"""Application configuration via environment variables.

Centralized settings powered by pydantic-settings. Reads from the
project `.env` file. Extend with project-specific keys (database URL,
Qdrant endpoint, LLM provider keys) as the system grows.
"""
from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the AcademicOS backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Project metadata
    PROJECT_NAME: str = "AcademicOS"
    VERSION: str = "0.1.0"
    DESCRIPTION: str = "Backend API for AcademicOS."
    API_V1_PREFIX: str = "/api/v1"

    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    # Database (placeholders — wire up with PostgreSQL later)
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/academicos"

    # Qdrant vector store (placeholder)
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION: str = "academicos"

    # LLM provider keys (placeholders)
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    # Storage
    UPLOAD_DIR: str = "app/uploads"
    MAX_UPLOAD_SIZE_MB: int = 50

    # Security
    SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor."""
    return Settings()


settings = get_settings()
