from __future__ import annotations

import asyncio
import hashlib
from typing import Any, cast

from aio_pika.abc import AbstractChannel
from minio import Minio
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.minio_client import MINIO_BUCKET_TEMP, MINIO_BUCKET_FINAL
from app.core.rabbitmq_client import RABBITMQ_QUEUE_FILE_TASKS
from app.core.constants import RedisKey
from app.crud import FileChunksCRUD, FileStorageCRUD
from app.models import FileChunksStatus, FileStorageStatus
from app.models import FileStorage, User
from app.models.users import UserRole
from app.schemas.file_storage import (
    FileChunkUploadIn,
    FileSaveDTO,
)

logger = get_logger(__name__)


async def _put_object_with_retry(
    *,
    minio_client: Minio,
    temp_bucket: str,
    chunk_object_name: str,
    payload,
    file_obj,
    length: int,
    max_retries: int = 3,
) -> tuple[str | None, int]:
    """
    上传文件分片到 MinIO。
    返回: chunk_md5 (占位，由外部计算), retry_count
    """
    retry_count = 0
    last_exc: Exception | None = None
    loop = asyncio.get_running_loop()

    for attempt in range(1, max_retries + 1):
        try:
            # 每次重试前，必须要把 file_obj 指针重置回 0
            if attempt > 1:
                file_obj.seek(0)

            # 将阻塞的 MinIO 调用放入线程池执行
            # 注意：file_obj 必须是线程安全的，UploadFile.file 是 SpooledTemporaryFile，通常是线程安全的
            await loop.run_in_executor(
                None,
                lambda: minio_client.put_object(
                    bucket_name=temp_bucket,
                    object_name=chunk_object_name,
                    data=file_obj,
                    length=length,
                    content_type=payload.content_type,
                ),
            )

            logger.info(
                "分片上传成功：object_name={}, 共尝试了 {} 次。",
                chunk_object_name,
                attempt,
            )
            # 返回 None 作为 chunk_md5，因为已经在外部计算并使用了
            return None, retry_count
        except Exception as exc:
            last_exc = exc
            retry_count += 1
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
        db: AsyncSession,
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

    async def save_file_metadata(
        self,
        user: User,
        payload: FileSaveDTO,
        bucket_name: str,
    ) -> FileStorage:
        """
        保存文件元数据到数据库。

        Args:
            user: 当前上传文件的用户对象
            payload: 包含文件元信息的 DTO 对象
            bucket_name: 存储桶名称（临时或正式）
        Returns:
            FileStorage: 保存后的文件元数据对象
        """

        # 权限控制：普通用户不能上传公共文件
        if user.role != UserRole.ADMIN.value:
            payload.is_public = False

        logger.info(
            "保存文件元数据：user_id={}, filename={}, is_public={}",
            user.id,
            payload.file_name,
            payload.is_public,
        )

        return await FileStorageCRUD.create_file_async(
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

        bitmap_key = RedisKey.UPLOAD_FILE_CHUNKS_BITMAP.format(
            user.id, payload.file_md5
        )
        file_storage_meta_key = RedisKey.FILE_STORAGE_METADATA.format(
            user.id, payload.file_md5
        )

        existing_obj: FileStorage | None = None

        # 优先用 Redis 判断是否已有任务；没有 Redis 则不走该分支
        has_redis_task = False
        if self.redis is not None:
            redis_client = cast(Any, self.redis)
            has_redis_task = (
                await redis_client.hget(file_storage_meta_key, "status")
            ) is not None

        # 满足以下任一条件才查 DB：
        # 1) Redis 表示已有任务：需要确认 DB 记录真实存在（防脏数据）
        # 2) 没有 Redis：只能依赖 DB 判定是否已有任务
        if has_redis_task or self.redis is None:
            existing_obj = await FileStorageCRUD.get_file_by_object_name_async(
                self.db, user.id, f"{payload.file_md5}/{payload.file_name}"
            )

        # 最终是否“已存在任务”以 DB 为准；若 Redis 有但 DB 无，则视为不存在（后面会重新创建）
        existing = existing_obj is not None

        # 若已有记录，但 content_type 缺失或为通用类型，或文件处于 FAILED，则更新
        if existing_obj is not None:
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
                await self.db.commit()

        # 第一片分片到达时创建原始文件元信息到 mysql 中
        if not existing:
            # 初始化文件元信息到数据库
            file_save_dto = FileSaveDTO(
                file_name=payload.file_name,
                content_type=payload.content_type,
                file_md5=payload.file_md5,
                file_size=payload.file_size,
                is_public=payload.is_public,
                status=FileStorageStatus.UPLOADING.value,
            )
            existing_obj = await self.save_file_metadata(
                user=user, payload=file_save_dto, bucket_name=temp_bucket
            )

        # Ensure we have the file object to return ID
        if existing_obj is None:
            existing_obj = await FileStorageCRUD.get_file_by_object_name_async(
                self.db, user.id, f"{payload.file_md5}/{payload.file_name}"
            )

        # 2) 写入分片元信息（状态 0-上传中-UPLOADING）
        chunk_object_name = f"{payload.file_md5}/chunk_{payload.chunk_index:06d}"
        existing_chunk = await FileChunksCRUD.get_chunk_async(
            self.db, payload.file_md5, payload.chunk_index
        )
        if existing_chunk and existing_chunk.status == FileChunksStatus.UPLOADED.value:
            logger.info(
                "分片已上传，跳过写入：file_md5={}, chunk_index={}",
                payload.file_md5,
                payload.chunk_index,
            )
            return {
                "file_md5": payload.file_md5,
                "chunk_md5": existing_chunk.etag,
                "chunk_index": payload.chunk_index,
                "uploaded": True,
                "file_id": existing_obj.id if existing_obj else None,
            }

        await FileChunksCRUD.create_chunk_async(
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
                # 使用流式读取计算 MD5，避免一次性加载到内存
                md5_hash = hashlib.md5()
                file_obj = file_chunk.file
                file_obj.seek(0)
                while chunk := file_obj.read(8192):  # 8KB 块
                    md5_hash.update(chunk)
                chunk_md5 = md5_hash.hexdigest()

                # 重置文件指针
                file_obj.seek(0)

                # 获取实际大小 (虽然 payload.chunk_size 应该一致，但保险起见)
                # SpooledTemporaryFile 有时候没有 len()，所以用 seek/tell 或者信任 payload
                # 这里假设 payload.chunk_size 是准确的，或者我们已经在上面读完了一遍
                # 更稳妥的是用 tell()
                file_obj.seek(0, 2)
                actual_size = file_obj.tell()
                file_obj.seek(0)

                _, retry_count = await _put_object_with_retry(
                    minio_client=self.minio,
                    temp_bucket=temp_bucket,
                    chunk_object_name=chunk_object_name,
                    payload=payload,
                    file_obj=file_obj,
                    length=actual_size,
                    max_retries=3,  # 最多重试3次
                )
                await FileChunksCRUD.update_chunk_etag_async(
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
                    await FileChunksCRUD.update_chunk_status_async(
                        self.db,
                        payload.file_md5,
                        payload.chunk_index,
                        FileChunksStatus.FAILED.value,  # 标记分片失败
                    )
                    file_obj = await FileStorageCRUD.get_file_by_object_name_async(
                        self.db, user.id, f"{payload.file_md5}/{payload.file_name}"
                    )
                    if file_obj:
                        await FileStorageCRUD.update_file_status_async(
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
                            # MinIO remove_object needs to be offloaded too if we want to be pure async
                            loop = asyncio.get_running_loop()
                            await loop.run_in_executor(
                                None,
                                lambda: self.minio.remove_object(
                                    temp_bucket, chunk_object_name
                                ),
                            )
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
        await FileChunksCRUD.update_chunk_status_async(
            db=self.db,
            file_md5=payload.file_md5,
            chunk_index=payload.chunk_index,
            status=FileChunksStatus.UPLOADED.value,
        )

        # 6) 判断是否全部上传完成，若完成则发送 MQ
        if self.redis is not None:
            redis_client = cast(Any, self.redis)
            meta_total_chunks = await redis_client.hget(
                file_storage_meta_key, "total_chunks"
            )
            expected_total = payload.total_chunks
            if meta_total_chunks is not None:
                try:
                    expected_total = int(meta_total_chunks)
                except (TypeError, ValueError):
                    expected_total = payload.total_chunks

            uploaded = await redis_client.bitcount(bitmap_key)
            # 校验：bitmap 完整 + 分片数量一致
            chunk_count = await FileChunksCRUD.count_chunks_async(
                self.db, payload.file_md5
            )
            if uploaded == expected_total and chunk_count == expected_total:
                if self.rabbitmq_channel is not None:
                    import json
                    from aio_pika import Message

                    await self.rabbitmq_channel.default_exchange.publish(
                        Message(
                            body=json.dumps(
                                {
                                    "user_id": user.id,
                                    "file_md5": payload.file_md5,
                                    "total_chunks": expected_total,
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
            "file_id": existing_obj.id if existing_obj else None,
        }

    async def upload_is_complete(self, user: User, file_id: int) -> int:
        """TODO: 查询完整文件是否已经完成上传，目前还是初步设计。

        说明：
        - 若文件已完成上传，返回 FileStorage.status (0-上传中，1-已上传，2-已完成向量化，3-失败)
        - 目前仅通过数据库中文件状态进行判断
        - 后续可结合 Redis 进行更精细的状态管理
        """

        logger.debug(
            "查询文件上传完成状态：user_id={}, file_id={}",
            user.id,
            file_id,
        )

        file_obj = await FileStorageCRUD.get_user_file_async(self.db, file_id, user.id)
        if not file_obj:
            raise ValueError("文件不存在或无权限")

        return file_obj.status
