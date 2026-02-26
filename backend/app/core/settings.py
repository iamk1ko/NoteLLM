from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List

from app.core.logging import get_logger

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, model_validator, computed_field

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
        extra="ignore",
    )

    APP_NAME: str = "Pai-School Backend"
    API_V1_PREFIX: str = "/api/v1"

    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    BLSC_API_KEY: str | None = None
    BLSC_BASE_URL: str | None = None
    LLM_MODEL: str = "DeepSeek-V3.2"
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 2048

    # Chat Memory - MinIO Bucket
    MEMORY_BUCKET: str = "chat-memories"

    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 3306
    DB_NAME: str = "pai_school"
    DB_USER: str = "root"
    DB_PASSWORD: str = "root"
    DATABASE_URL: str = ""
    DB_ECHO: bool = False

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
    EMBEDDING_MODEL_NAME: str = "BAAI/bge-m3"
    EMBEDDING_DEVICE: str = "cpu"

    VECTOR_COLLECTION: str = "knowledge_base"
    VECTOR_BATCH_SIZE: int = 64
    VECTOR_MEMORY_THRESHOLD_MB: int = 32
    VECTOR_TASK_TTL_SECONDS: int = 86400
    AUTH_SESSION_TTL_SECONDS: int = 604800

    # Vector Store Config
    VS_CONTENT_MAX_LEN: int = 4096
    VS_SECTION_MAX_LEN: int = 512
    VS_FILE_MD5_MAX_LEN: int = 64
    VS_BATCH_SIZE: int = 100

    # RAG Config
    RAG_HISTORY_LIMIT: int = 8
    RAG_CACHE_TTL: int = 300
    RAG_RANKER_ALPHA: float = 0.7
    RAG_TOP_K: int = 3

    # Chat Memory Config
    # Redis 短期记忆 - 滑动窗口大小
    REDIS_MEMORY_LIMIT: int = 20
    # Markdown 长期记忆 - 最大字符数
    MEMORY_MAX_CHARS: int = 12000

    # Milvus
    # 兼容两种配置方式：
    # 1) 推荐：MILVUS_URI=http://localhost:19530
    # 2) 兼容：MILVUS_HOST=127.0.0.1 + MILVUS_PORT=19530（旧配置/更直观）
    MILVUS_URI: str = ""
    MILVUS_HOST: str = Field(default="127.0.0.1")
    MILVUS_PORT: int = Field(default=19530)

    @computed_field
    @property
    def sync_database_url(self) -> str:
        """获取同步数据库连接字符串 (mysql+pymysql)。"""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )

    @computed_field
    @property
    def async_database_url(self) -> str:
        """获取异步数据库连接字符串 (mysql+aiomysql)。"""
        # 如果环境变量里显式配了 async url (e.g. ASYNC_DATABASE_URL)，这里也可以读
        # 目前简单起见，直接替换 driver
        sync_url = self.sync_database_url
        return sync_url.replace("mysql+pymysql", "mysql+aiomysql")

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
