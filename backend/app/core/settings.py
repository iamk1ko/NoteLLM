from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field, model_validator, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.logging import get_logger

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

logger = get_logger(__name__)


class Settings(BaseSettings):
    """项目的默认配置。
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
        extra="ignore",  # 如果 .env 或环境变量里出现了 Settings 未声明的字段名（“多余键”），会被忽略而不是报错；
        # 这样可以在不同环境复用同一个 .env，或留下一些暂未使用的配置项而不影响启动。
    )

    APP_NAME: str = "NoteLLM Backend"
    API_V1_PREFIX: str = "/api/v1"

    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # LLM 配置
    BLSC_API_KEY: str | None = None
    BLSC_BASE_URL: str | None = None
    LLM_MODEL: str = "DeepSeek-V3.2"
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 2048

    # MinIO 配置
    MINIO_ENDPOINT: str = "127.0.0.1:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_SECURE: bool = False

    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 3306
    DB_NAME: str = "pai_school"
    DB_USER: str = "root"
    DB_PASSWORD: str = "root"
    DATABASE_URL: str = ""
    DB_DRIVER: str = "mysql+aiomysql"
    DB_ECHO: bool = False  # SQLAlchemy 是否输出执行的 SQL 语句到日志，生产环境建议关闭，开发环境可开启调试 SQL。
    DB_POOL_SIZE: int = (
        10  # 数据库连接池的大小，生产环境建议根据并发量调整，开发环境默认10通常足够。
    )
    DB_MAX_OVERFLOW: int = 20  # 连接池外最多允许的连接数，设置为0表示不允许超过 pool_size 的连接，生产环境可适当调整以应对突发流量。
    DB_POOL_TIMEOUT: int = 30  # 获取连接的超时时间（秒），生产环境建议设置合理的超时时间以避免长时间等待，开发环境默认30秒通常足够。

    LOG_LEVEL: str = "INFO"

    REDIS_URL: str = "redis://127.0.0.1:6379/0"
    REDIS_MAX_CONNECTIONS: int = 20
    # 文件上传锁 TTL，单位秒。设置合理的过期时间可以防止死锁（例如上传过程中发生异常导致锁未释放），同时也允许在上传过程中其他请求等待锁释放。
    REDIS_UPLOAD_LOCK_TTL_SECONDS: int = 300
    # 会话锁 TTL，单位秒。用于控制同一用户的并发请求，避免短时间内重复创建会话或处理同一会话的多个请求。设置较短的 TTL 可以减少用户等待时间，同时也能有效防止重复操作。
    REDIS_SESSION_LOCK_TTL_SECONDS: int = 10

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
    EMBEDDING_MODEL_NAME: str = "GLM-Embedding-3"

    VECTOR_COLLECTION: str = "knowledge_base"
    VECTOR_BATCH_SIZE: int = 64
    VECTOR_MEMORY_THRESHOLD_MB: int = 32
    VECTOR_TASK_TTL_SECONDS: int = 86400
    AUTH_SESSION_TTL_SECONDS: int = 604800  # 7天，单位秒

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
            f"{self.DB_DRIVER}://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )

    @model_validator(mode="after")
    def _build_milvus_uri(self) -> "Settings":
        # 如果显式配置了 MILVUS_URI，就直接用；否则由 host/port 组装。
        if not (self.MILVUS_URI or "").strip():
            self.MILVUS_URI = f"http://{self.MILVUS_HOST}:{self.MILVUS_PORT}"
        return self

    def cors_origins_list(self) -> List[str]:
        # 解析 CORS_ORIGINS 字符串为列表，支持逗号分隔和通配符
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
