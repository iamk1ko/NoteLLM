from __future__ import annotations

from app.core.logging import get_logger
from app.core.minio_client import get_minio_client
from app.core.redis_client import get_redis_client
from app.crud import FileStorageCRUD
from app.core.constants import RedisKey
from app.services.vectorization import MilvusVectorStore

logger = get_logger(__name__)


class FileCleanupService:
    """文件清理服务（硬删除）。

    说明：
    - 删除文件时同时清理 MinIO / Redis / Milvus / MySQL
    - 不走软删除与异步队列
    """

    def __init__(self, *, db, milvus: MilvusVectorStore | None = None):
        self.db = db
        self.milvus = milvus
        self.redis = get_redis_client()
        self.minio = get_minio_client()

    async def execute_cleanup_direct(
        self,
        *,
        file_id: int,
        user_id: int | None,
        file_md5: str | None,
        bucket_name: str | None,
        object_name: str | None,
    ) -> None:
        """直接清理文件相关资源（硬删除）。"""

        # 1) 清理 MinIO
        if bucket_name and object_name:
            try:
                self.minio.remove_object(bucket_name, object_name)
                logger.info(
                    "MinIO 对象删除成功：file_id={}, bucket={}, object={}",
                    file_id,
                    bucket_name,
                    object_name,
                )
            except Exception as e:
                logger.error(
                    "MinIO 对象删除失败：file_id={}, bucket={}, object={}, error={}",
                    file_id,
                    bucket_name,
                    object_name,
                    e,
                    exc_info=True,
                )

        # 2) 清理 Redis 缓存（上传元信息/bitmap）
        if user_id is not None and file_md5:
            try:
                await self.redis.delete(
                    RedisKey.FILE_STORAGE_METADATA.format(user_id, file_md5),
                    RedisKey.UPLOAD_FILE_CHUNKS_BITMAP.format(user_id, file_md5),
                    RedisKey.FILE_VECTORIZATION_TASK_STATUS.format(file_md5),
                    RedisKey.FILE_VECTORIZATION_TASK_ERROR.format(file_md5),
                    RedisKey.FILE_VECTORIZATION_TASK_STAGE.format(file_md5),
                    RedisKey.FILE_VECTORIZATION_TASK_ERROR_CODE.format(file_md5),
                    RedisKey.FILE_VECTORIZATION_TASK_ERROR_MESSAGE.format(file_md5),
                    RedisKey.FILE_VECTORIZATION_TASK_RETRYABLE.format(file_md5),
                    RedisKey.FILE_VECTORIZATION_TASK_UPDATED_AT.format(file_md5),
                    RedisKey.FILE_VECTORIZATION_TASK_CURSOR.format(file_md5),
                )
                logger.info(
                    "Redis 上传缓存清理完成：file_id={}, user_id={}, file_md5={}",
                    file_id,
                    user_id,
                    file_md5,
                )
            except Exception as e:
                logger.error(
                    "Redis 上传缓存清理失败：file_id={}, error={}",
                    file_id,
                    e,
                    exc_info=True,
                )

        # 3) 清理 Milvus 向量
        if self.milvus is not None:
            deleted_count = await self.milvus.delete_by_file_id(file_id)
            if deleted_count == 0:
                logger.warning("Milvus 向量删除为空：file_id={}", file_id)

        # 4) 删除 MySQL 记录
        await FileStorageCRUD.delete_file_async(self.db, file_id)
        logger.info("文件记录已硬删除：file_id={}", file_id)
