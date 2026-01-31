from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List
from app.core.logging import get_logger

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

logger = get_logger(__name__)


class Settings(BaseSettings):
    """Project settings.

    Similar to SpringBoot's application.yml + @ConfigurationProperties.

    Env vars examples:
      - APP_NAME=My-RAG-Demo
      - API_V1_PREFIX=/api/v1
      - CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
      - BLSC_API_KEY=...
      - BLSC_BASE_URL=https://...
      - DATABASE_URL=sqlite:///database/my_rag.db
      - LOG_LEVEL=INFO
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    APP_NAME: str = "My-RAG-Demo"
    API_V1_PREFIX: str = "/api/v1"

    # Comma-separated list in env var; we parse it manually.
    CORS_ORIGINS: str = "*"

    # External service (your BLSC proxy)
    BLSC_API_KEY: str | None = None
    BLSC_BASE_URL: str | None = None

    # Database
    DATABASE_URL: str = f"sqlite:///{(ROOT_DIR / 'database' / 'my_rag.db').as_posix()}"
    # logger.info(f"DATABASE_URL: {DATABASE_URL}")

    # Logging
    LOG_LEVEL: str = "INFO"

    def cors_origins_list(self) -> List[str]:
        raw = (self.CORS_ORIGINS or "").strip()
        if not raw:
            return []
        if raw == "*":
            return ["*"]
        return [part.strip() for part in raw.split(",") if part.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
