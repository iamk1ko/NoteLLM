from __future__ import annotations

from minio import Minio

from app.core.settings import get_settings


def get_minio_client() -> Minio:
    """获取 MinIO 客户端。

    说明：
    - MinIO 走 HTTP（MINIO_SECURE=False）
    - 连接信息来自 Settings
    """

    settings = get_settings()
    return Minio(
        endpoint=settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )


def get_minio_buckets() -> tuple[str, str]:
    """获取 MinIO 临时桶与正式桶名称。

    返回值：
    - (temp_bucket, final_bucket)
    """

    settings = get_settings()
    return settings.MINIO_BUCKET_TEMP, settings.MINIO_BUCKET_FINAL
