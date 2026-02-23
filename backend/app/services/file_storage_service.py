from __future__ import annotations

import asyncio
import hashlib
import io
from typing import Any, cast, Coroutine

from aio_pika.abc import AbstractChannel
from minio import Minio
from redis.asyncio import Redis
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.minio_client import MINIO_BUCKET_TEMP, MINIO_BUCKET_FINAL
from app.core.rabbitmq_client import RABBITMQ_QUEUE_FILE_TASKS
from app.core.redis_client import (
    FILE_STORAGE_METADATA_KEY,
    UPLOAD_FILE_CHUNKS_BITMAP_KEY,
)
from app.crud import FileChunksCRUD, FileStorageCRUD
from app.models import FileChunksStatus, FileStorageStatus
from app.models import FileStorage, User
from app.models.users import UserRole
from app.schemas.file_storage import (
    FileChunkUploadIn,
    FileSaveDTO,
)

logger = get_logger(__name__)


class FileStorageService:
    """文件存储业务服务层。

    说明：
    - 负责文件元数据的创建与查询
    - 权限控制：普通用户只能上传私有文件
    - 管理员可以上传公共文件
    - 文件分块与向量化处理接口预留

    Redis 结构建议（断点续传）：
    - bitmap: upload:bitmap:{user_id}:{file_md5}
      bit_index = chunk_index
    - meta: upload:meta:{user_id}:{file_md5}
      fields: total_chunks/total_size/file_name/content_type/is_public/status
    """

    def __init__(
        self,
        db: Session,
        redis_client: Redis | None = None,
        minio_client: Minio | None = None,
        rabbitmq_channel: AbstractChannel | None = None,
    ):
        """初始化文件服务。

        说明：
        - 允许通过依赖注入传入 Redis / MinIO / RabbitMQ
        - 便于在 API 层统一管理资源
        """

        self.db = db
        self.redis = redis_client
        self.minio = minio_client
        self.rabbitmq_channel = rabbitmq_channel

    def save_file_metadata(
        self,
        user: User,
        payload: FileSaveDTO,
        bucket_name: str,
    ) -> FileStorage:
        """TODO: 上传文件, 目前并未实际使用。有 upload_chunk 替代。后续可以考虑删除。"""

        # 权限控制：普通用户不能上传公共文件
        if user.role != UserRole.ADMIN.value:
            payload.is_public = False

        logger.info(
            "保存文件元数据：user_id={}, filename={}, is_public={}",
            user.id,
            payload.file_name,
            payload.is_public,
        )

        return FileStorageCRUD.create_file(
            db=self.db,
            user_id=user.id,
            filename=payload.file_name,
            content_type=payload.content_type,
            file_size=payload.file_size,
            bucket_name=bucket_name,
            object_name=f"{payload.file_md5}/{payload.file_name}",
            etag=payload.file_md5,
            is_public=payload.is_public,
            status=payload.status if user.role == UserRole.ADMIN.value else False,
        )

    async def upload_chunk(
        self,
        user: User,
        payload: FileChunkUploadIn,
        file_chunk,
    ) -> dict:
        """上传分片（业务逻辑占位）。"""

        logger.info(
            "分片上传：user_id={}, file_md5={}, chunk_index={}",
            user.id,
            payload.file_md5,
            payload.chunk_index,
        )

        # 0) 重试计数 key
        # 仅当不存在时创建，避免重复
        temp_bucket = MINIO_BUCKET_TEMP
        final_bucket = MINIO_BUCKET_FINAL

        bitmap_key = UPLOAD_FILE_CHUNKS_BITMAP_KEY.format(user.id, payload.file_md5)
        file_storage_meta_key = FILE_STORAGE_METADATA_KEY.format(
            user.id, payload.file_md5
        )

        existing_obj: FileStorage | None = None
        existing = None
        if self.redis is not None:
            # 用 Redis meta 简单判断是否已有任务
            redis_client = cast(Any, self.redis)
            existing = await redis_client.hget(file_storage_meta_key, "status")
        else:
            # 没有 Redis 时通过数据库兜底判断是否已有任务
            existing_obj = FileStorageCRUD.get_file_by_object_name(
                self.db, user.id, f"{payload.file_md5}/{payload.file_name}"
            )
            existing = "exists" if existing_obj else None

        if existing is not None and existing_obj is None:
            existing_obj = FileStorageCRUD.get_file_by_object_name(
                self.db, user.id, f"{payload.file_md5}/{payload.file_name}"
            )

        # 若已有记录，但 content_type 缺失或为通用类型，则更新为本次上传的类型
        if existing is not None and existing_obj:
            should_update_type = existing_obj.content_type in (
                None,
                "",
                "application/octet-stream",
            )
            should_update_status = existing_obj.status == FileStorageStatus.FAILED.value
            if should_update_type or should_update_status:
                if should_update_type:
                    existing_obj.content_type = payload.content_type
                if should_update_status:
                    existing_obj.status = FileStorageStatus.UPLOADING.value
                self.db.commit()

        # 第一片分片到达时创建原始文件元信息到 mysql 中
        if existing is None:
            # 初始化文件元信息到数据库
            file_save_dto = FileSaveDTO(
                file_name=payload.file_name,
                content_type=payload.content_type,
                file_md5=payload.file_md5,
                file_size=payload.file_size,
                is_public=payload.is_public,
                status=FileStorageStatus.UPLOADING.value,
            )
            self.save_file_metadata(
                user=user, payload=file_save_dto, bucket_name=temp_bucket
            )

        # 2) 写入分片元信息（状态 0-上传中-UPLOADING）
        chunk_object_name = f"{payload.file_md5}/chunk_{payload.chunk_index:06d}"
        FileChunksCRUD.create_chunk(
            db=self.db,
            file_md5=payload.file_md5,
            chunk_index=payload.chunk_index,
            chunk_size=payload.chunk_size,
            bucket_name=temp_bucket,
            object_name=chunk_object_name,
            status=FileChunksStatus.UPLOADING.value,
            etag=None,  # 初始为空，上传后更新
        )

        # 3) 上传到 MinIO 临时桶（含 MD5 计算）
        chunk_md5, retry_count = None, 0
        if self.minio is not None:
            try:
                chunk_bytes = file_chunk.file.read()

                chunk_md5, retry_count = await self._put_object_with_retry(
                    minio_client=self.minio,
                    temp_bucket=temp_bucket,
                    chunk_object_name=chunk_object_name,
                    payload=payload,
                    chunk_bytes=chunk_bytes,
                    max_retries=3,  # 最多重试3次
                )
                FileChunksCRUD.update_chunk_etag(
                    self.db,
                    payload.file_md5,
                    payload.chunk_index,
                    chunk_md5,
                )
            except Exception as exc:
                # 超过3次重试，则标记 分片和文件 失败
                if retry_count >= 3:
                    logger.error(
                        "分片上传失败超过重试次数，标记为失败，并清理相关信息：user_id={}, file_md5={}, chunk_index={}",
                        user.id,
                        payload.file_md5,
                        payload.chunk_index,
                    )
                    FileChunksCRUD.update_chunk_status(
                        self.db,
                        payload.file_md5,
                        payload.chunk_index,
                        FileChunksStatus.FAILED.value,  # 标记分片失败
                    )
                    file_obj = FileStorageCRUD.get_file_by_object_name(
                        self.db, user.id, f"{payload.file_md5}/{payload.file_name}"
                    )
                    if file_obj:
                        FileStorageCRUD.update_file_status(
                            self.db,
                            file_id=file_obj.id,
                            status=FileStorageStatus.FAILED.value,  # 标记文件失败
                        )
                    if self.redis is not None:
                        redis_client = cast(Any, self.redis)
                        await redis_client.hset(
                            file_storage_meta_key,
                            "status",
                            FileStorageStatus.FAILED.value,  # Redis 中标记文件失败
                        )
                    if self.minio is not None:
                        try:
                            self.minio.remove_object(
                                temp_bucket, chunk_object_name
                            )  # 清理失败分片对象
                        except Exception:
                            logger.exception(
                                "清理 MinIO 中失败分片对象失败：object_name={}",
                                chunk_object_name,
                            )
                    # 返回失败响应给调用者（API 层需据此返回合适的 HTTP 状态）
                    return {
                        "file_md5": payload.file_md5,
                        "chunk_md5": None,
                        "chunk_index": payload.chunk_index,
                        "uploaded": False,
                        "error": "chunk upload failed after retries",
                    }

                # 未超过重试阈值：记录并返回局部失败，客户端可重试
                logger.warning(
                    "分片上传异常，已增加重试计数：object_name={}, retry_count={}, exc={}",
                    chunk_object_name,
                    retry_count,
                    exc,
                )
                return {
                    "file_md5": payload.file_md5,
                    "chunk_md5": None,
                    "chunk_index": payload.chunk_index,
                    "uploaded": False,
                    "retry_count": retry_count,
                    "error": str(exc),
                }

        # 4) Redis bitmap 标记分片上传成功
        if self.redis is not None:
            redis_client = cast(Any, self.redis)

            # 1) 标记该分片已上传
            await redis_client.setbit(bitmap_key, payload.chunk_index, 1)

            # 2) 只维护元信息字段，但避免每次都把 status 重置为 uploading
            #    解释：
            #    - status 表示“整体上传任务状态”（即 file_storage 文件的状态），正确流转应是 uploading -> merged(或 completed)
            #    - 如果每个分片都写 status=uploading，可能覆盖后续步骤写入的 merged
            await redis_client.hset(
                file_storage_meta_key,
                mapping={
                    "total_chunks": payload.total_chunks,
                    "total_size": payload.file_size,
                    "file_name": payload.file_name,
                    "content_type": payload.content_type,
                    "is_public": int(payload.is_public),
                },
            )

            # 3) 仅当 status 字段不存在时，初始化为 uploading（避免覆盖 merged）
            #    Redis 的 HSETNX: field 不存在才会写入
            await redis_client.hsetnx(
                file_storage_meta_key, "status", FileStorageStatus.UPLOADING.value
            )

        # 5) 更新分片状态为已上传 (UPLOADED)
        FileChunksCRUD.update_chunk_status(
            db=self.db,
            file_md5=payload.file_md5,
            chunk_index=payload.chunk_index,
            status=FileChunksStatus.UPLOADED.value,
        )

        # 6) 判断是否全部上传完成，若完成则发送 MQ
        if self.redis is not None:
            redis_client = cast(Any, self.redis)
            uploaded = await redis_client.bitcount(bitmap_key)
            # 校验：bitmap 完整 + 分片数量一致
            chunk_count = FileChunksCRUD.count_chunks(self.db, payload.file_md5)
            if uploaded == payload.total_chunks and chunk_count == payload.total_chunks:
                if self.rabbitmq_channel is not None:
                    import json
                    from aio_pika import Message

                    await self.rabbitmq_channel.default_exchange.publish(
                        Message(
                            body=json.dumps(
                                {
                                    "user_id": user.id,
                                    "file_md5": payload.file_md5,
                                    "total_chunks": payload.total_chunks,
                                    "file_name": payload.file_name,
                                },
                                ensure_ascii=False,
                            ).encode("utf-8")
                        ),
                        routing_key=RABBITMQ_QUEUE_FILE_TASKS,
                    )

        return {
            "file_md5": payload.file_md5,
            "chunk_md5": chunk_md5,
            "chunk_index": payload.chunk_index,
            "uploaded": True,
        }

    async def _put_object_with_retry(
        self,
        *,
        minio_client: Minio,
        temp_bucket: str,
        chunk_object_name: str,
        payload,
        chunk_bytes: bytes,
        max_retries: int = 3,
    ) -> tuple[str, int | Any]:
        """
        返回: chunk_md5 (作为 etag)
        说明:
        - 在同一次请求中重试 max_retries 次
        - 每失败一次就把 retry_count +1
        - 超过阈值抛出最后一次异常
        """
        retry_count = 0
        chunk_md5 = hashlib.md5(chunk_bytes).hexdigest()

        last_exc: Exception | None = None
        for attempt in range(1, max_retries + 1):
            try:
                minio_client.put_object(
                    bucket_name=temp_bucket,
                    object_name=chunk_object_name,
                    data=io.BytesIO(chunk_bytes),
                    length=len(chunk_bytes),
                    content_type=payload.content_type,
                )
                logger.info(
                    "分片上传成功：object_name={}, 共尝试了 {} 次。",
                    chunk_object_name,
                    attempt,
                )
                return chunk_md5, retry_count
            except Exception as exc:
                last_exc = exc

                # 重试次数 +1
                retry_count += 1
                # 简单退避: 0.2s, 0.4s, 0.8s ...
                if retry_count < max_retries:
                    await asyncio.sleep(0.2 * (2 ** (retry_count - 1)))
                    logger.warning(
                        "分片上传失败，正在重试：object_name={}, 尝试第 {} 次。",
                        chunk_object_name,
                        retry_count,
                    )
                    continue

                raise

        if last_exc is not None:
            raise last_exc
        raise RuntimeError("上传失败")  # 理论上到不了

    async def upload_is_complete(self, user: User, file_id: int) -> int:
        """TODO: 查询完整文件是否已经完成上传，目前还是初步设计。

        说明：
        - 若文件已完成上传，返回 FileStorage.status (0-上传中，1-已上传，2-已向量化，3-失败)
        - 目前仅通过数据库中文件状态进行判断
        - 后续可结合 Redis 进行更精细的状态管理
        """

        logger.info(
            "查询文件上传完成状态：user_id={}, file_id={}",
            user.id,
            file_id,
        )

        file_obj = FileStorageCRUD.get_user_file(self.db, file_id, user.id)
        if not file_obj:
            raise ValueError("文件不存在或无权限")

        return file_obj.status
