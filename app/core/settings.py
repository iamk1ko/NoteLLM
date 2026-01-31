from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Project settings.

    Similar to SpringBoot's application.yml + @ConfigurationProperties.

    Env vars examples:
      - APP_NAME=My-RAG-Demo
      - API_V1_PREFIX=/api/v1
      - CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
      - BLSC_API_KEY=...
      - BLSC_BASE_URL=https://...
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

