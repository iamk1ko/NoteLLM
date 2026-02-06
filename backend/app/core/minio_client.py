from __future__ import annotations

from minio import Minio

from app.core.settings import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

MINIO_BUCKET_TEMP: str = "upload-temp"  # 临时桶，用于分片上传
MINIO_BUCKET_FINAL: str = "upload-final"  # 正式桶，用于存储最终文件


def get_minio_client() -> Minio:
    """获取 MinIO 客户端。

    说明：
    - MinIO 走 HTTP（MINIO_SECURE=False）
    - 连接信息来自 Settings
    """

    settings = get_settings()
    minio = Minio(endpoint=settings.MINIO_ENDPOINT,
                  access_key=settings.MINIO_ACCESS_KEY,
                  secret_key=settings.MINIO_SECRET_KEY,
                  secure=settings.MINIO_SECURE,
                  )

    # 初始化桶, 如果不存在则创建
    init_minio_buckets(minio)

    return minio


def init_minio_buckets(minio_client: Minio) -> None:
    """初始化 MinIO 桶（如果不存在则创建）。"""

    temp_bucket, final_bucket = get_minio_buckets()

    for bucket_name in (temp_bucket, final_bucket):
        found = minio_client.bucket_exists(bucket_name)
        if not found:
            logger.info(f"MinIO 桶 '{bucket_name}' 不存在，正在创建...")
            minio_client.make_bucket(bucket_name)


def get_minio_buckets() -> tuple[str, str]:
    """获取 MinIO 临时桶与正式桶名称。

    返回值：
    - (temp_bucket, final_bucket)
    """
    return MINIO_BUCKET_TEMP, MINIO_BUCKET_FINAL
