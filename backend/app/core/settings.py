from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List

from app.core.logging import get_logger

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, model_validator

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

logger = get_logger(__name__)


class Settings(BaseSettings):
    """Project settings.

    Similar to SpringBoot's application.yml + @ConfigurationProperties.

    Env vars examples:
      - APP_NAME=Pai-School Backend
      - API_V1_PREFIX=/api/v1
      - CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
      - BLSC_API_KEY=...
      - BLSC_BASE_URL=https://...
        - DATABASE_URL=mysql+pymysql://user:password@127.0.0.1:3306/pai_school?charset=utf8mb4
        - DB_DRIVER=mysql+pymysql
        - DB_HOST=127.0.0.1
        - DB_PORT=3306
        - DB_NAME=pai_school
        - DB_USER=root
        - DB_PASSWORD=root
        - LOG_LEVEL=INFO
        - REDIS_URL=redis://:password@127.0.0.1:6379/0
        - MINIO_ENDPOINT=127.0.0.1:9000
        - MINIO_ACCESS_KEY=minioadmin
        - MINIO_SECRET_KEY=minioadmin
        - MINIO_SECURE=false
        - RABBITMQ_URL=amqp://guest:guest@127.0.0.1:5672/

    常见坑位说明（MySQL）:
      - 如果你使用的是 MySQL 8.x，且用户认证插件是默认的 caching_sha2_password/sha256_password，
        那么 pymysql 需要额外安装 cryptography，否则在首次连接时会报：
        RuntimeError: 'cryptography' package is required...
      - 两种解决思路：
        1) 推荐：在 Python 依赖里安装 cryptography（本项目已在 pyproject.toml 中声明）。
        2) 备选：把 MySQL 用户认证插件改成 mysql_native_password（需要 DBA 权限；不建议生产随意改）。
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        # 说明：默认 extra 行为在不同版本/配置下可能是 forbid。
        # 我们选择“显式声明需要的 env key”，比全局 ignore 更安全。
    )

    APP_NAME: str = "Pai-School Backend"
    API_V1_PREFIX: str = "/api/v1"

    CORS_ORIGINS: str = "*"

    BLSC_API_KEY: str | None = None
    BLSC_BASE_URL: str | None = None

    DB_DRIVER: str = "mysql+pymysql"
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 3306
    DB_NAME: str = "pai_school"
    DB_USER: str = "root"
    DB_PASSWORD: str = "root"
    DATABASE_URL: str = ""

    LOG_LEVEL: str = "DEBUG"

    REDIS_URL: str = "redis://127.0.0.1:6379/0"
    REDIS_MAX_CONNECTIONS: int = 20

    MINIO_ENDPOINT: str = "127.0.0.1:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_SECURE: bool = False

    RABBITMQ_URL: str = "amqp://admin:admin@127.0.0.1:5672/admin_vhost"

    # Vectorization settings
    EMBEDDING_DIM: int = 1024
    VECTOR_COLLECTION: str = "knowledge_base"
    VECTOR_BATCH_SIZE: int = 64
    VECTOR_MEMORY_THRESHOLD_MB: int = 32

    # Milvus
    # 兼容两种配置方式：
    # 1) 推荐：MILVUS_URI=http://localhost:19530
    # 2) 兼容：MILVUS_HOST=127.0.0.1 + MILVUS_PORT=19530（旧配置/更直观）
    MILVUS_URI: str = ""
    MILVUS_HOST: str = Field(default="127.0.0.1")
    MILVUS_PORT: int = Field(default=19530)

    @model_validator(mode="after")
    def _build_milvus_uri(self) -> "Settings":
        # 如果显式配置了 MILVUS_URI，就直接用；否则由 host/port 组装。
        if not (self.MILVUS_URI or "").strip():
            self.MILVUS_URI = f"http://{self.MILVUS_HOST}:{self.MILVUS_PORT}"
        return self

    def cors_origins_list(self) -> List[str]:
        raw = (self.CORS_ORIGINS or "").strip()
        if not raw:
            return []
        if raw == "*":
            return ["*"]
        return [part.strip() for part in raw.split(",") if part.strip()]

    def database_url(self) -> str:
        raw = (self.DATABASE_URL or "").strip()
        if raw:
            return raw
        return (
            f"{self.DB_DRIVER}://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
