from __future__ import annotations

from minio import Minio

from app.core.constants import MinIOBucket
from app.core.logging import get_logger
from app.core.settings import get_settings

logger = get_logger(__name__)


def get_minio_client() -> Minio:
    """创建 MinIO 客户端对象。

    重要说明：
    - 这个函数只负责"创建客户端对象"，不要在这里做任何网络 I/O（比如 bucket_exists）。
    - 桶初始化属于启动阶段的工作，应由 lifespan/InfraProvider 显式调用 `init_minio_buckets()`。
    """

    settings = get_settings()
    return Minio(
        endpoint=settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )


def init_minio_buckets(minio_client: Minio) -> None:
    """初始化 MinIO 桶（如果不存在则创建）。

    说明：
    - 这是"有副作用"的操作（会访问 MinIO），不要在模块 import 时执行。
    - 推荐在应用启动（lifespan）时执行一次。
    """

    for bucket in MinIOBucket:
        found = minio_client.bucket_exists(bucket.value)
        if not found:
            # 统一采用 {} 占位符（适配你项目当前 logger 配置风格）。
            logger.info("MinIO 桶 '{}' 不存在，正在创建...", bucket.value)
            minio_client.make_bucket(bucket.value)
