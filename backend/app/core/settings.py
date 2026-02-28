from __future__ import annotations

from functools import lru_cache
import os
from pathlib import Path
from typing import List

from app.core.logging import get_logger

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, model_validator, computed_field

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

logger = get_logger(__name__)


class Settings(BaseSettings):
    """Project settings.
    简要说明关系：
        - settings.py 是配置结构/默认值的定义（字段、类型、默认值、校验逻辑）。
        - .env/.env.dev/.env.test 是配置值的来源（运行时的数据）。
        - get_settings() 返回的配置值 优先级是：环境变量 > .env.{APP_ENV} > .env > settings.py 默认值。
    所以在别处调用 get_settings() 时，如果 .env 或系统环境变量里有对应字段，会覆盖 settings.py 里默认值。

    换句话说：
        - settings.py 决定“有哪些配置项”
        - .env.* 决定“这些配置项当前环境取什么值”

    如果你要新增一个配置：
    1) 必须在 settings.py 里加字段（否则代码根本不知道这个配置项）
    2) 在对应的 .env.* 中填值（可选，不填就用默认值）
    """

    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        case_sensitive=False,
        # 说明：默认 extra 行为在不同版本/配置下可能是 forbid。
        # 我们选择“显式声明需要的 env key”，比全局 ignore 更安全。
        extra="ignore",
    )

    APP_NAME: str = "NoteLLM Backend"
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

    # MQ Retry / DLQ
    MQ_RETRY_MAX_ATTEMPTS: int = 3
    # RabbitMQ TTL 级别的重试间隔（秒），支持逗号分隔的多级 backoff，例如 "10,30,120" 表示第一次重试间隔 10 秒，第二次 30 秒，第三次 120 秒。超过重试次数后进入 DLQ 或丢弃。
    MQ_RETRY_BACKOFF_SECONDS: str = "10,30,120"
    # 是否启用死信队列（DLQ）。启用后，超过重试次数的消息会被路由到 DLQ 进行后续分析/处理；禁用后，消息将被丢弃。建议生产环境启用以避免消息丢失。
    MQ_DLQ_ENABLED: bool = True
    # 是否在启动时强制重建队列（仅建议开发环境开启）。
    MQ_FORCE_RECREATE_QUEUES: bool = False

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
    # Redis 提供给 LLM 的短期记忆 - 滑动窗口大小
    REDIS_MEMORY_LIMIT: int = 10
    # Redis 短期记忆 - TTL（秒） - 过期后自动清理，避免无限增长占用内存；同时也意味着用户的短期记忆会在一段时间不活跃后被清空。
    REDIS_CHAT_TTL_SECONDS: int = 86400
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
    # env = (os.getenv("APP_ENV") or "dev").strip().lower()
    env_files = [
        # ROOT_DIR / f".env.{env}",
        ROOT_DIR / ".env",
    ]
    return Settings(_env_file=env_files)  # type: ignore[call-arg]
