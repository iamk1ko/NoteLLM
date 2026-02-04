from __future__ import annotations

import asyncio
from typing import Any, cast
import hashlib
import io

from sqlalchemy.orm import Session
from aio_pika.abc import AbstractChannel
from minio import Minio
from redis.asyncio import Redis

from app.core.logging import get_logger
from app.core.settings import get_settings
from app.crud.file_storage_crud import FileStorageCRUD
from app.crud.file_chunks_crud import FileChunksCRUD
from app.models import FileStorage, User
from app.models.file_chunks import FileChunksStatus
from app.models.users import UserRole
from app.models.file_storage import FileStorageStatus
from app.schemas.file_storage import (
    FileUploadCreate,
    FileChunkUploadIn,
    FileUploadCompleteIn,
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

    def upload_file(
            self,
            user: User,
            payload: FileUploadCreate,
            bucket_name: str,
            object_name: str,
            etag: str | None = None,
    ) -> FileStorage:
        """上传文件（仅保存元数据）。

        说明：
        - 这里只保存文件元数据，不处理实际文件上传
        - 文件内容应先上传到 MinIO，再调用此方法保存元数据

        参数说明：
        - user: 当前登录用户
        - payload: 文件元数据
        - bucket_name: 存储桶名称
        - object_name: 对象名称
        - etag: 文件 ETag（可选）
        """

        # 权限控制：普通用户不能上传公共文件
        if user.role != UserRole.ADMIN.value:
            payload.is_public = False

        logger.info(
            "保存文件元数据：user_id={}, filename={}, is_public={}",
            user.id,
            payload.filename,
            payload.is_public,
        )

        return FileStorageCRUD.create_file(
            db=self.db,
            user_id=user.id,
            filename=payload.filename,
            content_type=payload.content_type,
            file_size=payload.file_size,
            bucket_name=bucket_name,
            object_name=object_name,
            etag=etag,
            is_public=payload.is_public,
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
        settings = get_settings()
        temp_bucket = settings.MINIO_BUCKET_TEMP
        final_bucket = settings.MINIO_BUCKET_FINAL

        bitmap_key = f"upload:bitmap:{user.id}:{payload.file_md5}"
        file_storage_meta_key = f"upload:meta:{user.id}:{payload.file_md5}"
        retry_key = f"upload:retry:{user.id}:{payload.file_md5}:{payload.chunk_index}"

        if self.redis is not None:
            # 用 Redis meta 简单判断是否已有任务
            redis_client = cast(Any, self.redis)
            existing = await redis_client.hget(file_storage_meta_key, "status")
        else:
            # 没有 Redis 时通过数据库兜底判断是否已有任务
            existing_obj: FileStorage = FileStorageCRUD.get_file_by_object_name(
                self.db, user.id, f"{payload.file_md5}/{payload.file_name}"
            )
            existing = "exists" if existing_obj else None

        # 第一片分片到达时创建原始文件元信息到 mysql 中
        if existing is None:
            FileStorageCRUD.create_file(
                db=self.db,
                user_id=user.id,
                filename=payload.file_name,
                content_type=payload.content_type,
                file_size=payload.total_size,
                bucket_name=temp_bucket,
                object_name=f"{payload.file_md5}/{payload.file_name}",
                is_public=payload.is_public
                if user.role == UserRole.ADMIN.value
                else False,
                status=FileStorageStatus.UPLOADING.value,
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
        if self.minio is not None:
            try:
                chunk_bytes = file_chunk.file.read()

                chunk_md5 = await self._put_object_with_retry(
                    temp_bucket=temp_bucket,
                    chunk_object_name=chunk_object_name,
                    payload=payload,
                    chunk_bytes=chunk_bytes,
                    retry_key=retry_key,
                    max_retries=3,  # 最多重试3次
                )
                FileChunksCRUD.update_chunk_etag(
                    self.db,
                    payload.file_md5,
                    payload.chunk_index,
                    chunk_md5,
                )
            except Exception:
                retry_count = 0
                if self.redis is not None:
                    redis_client = cast(Any, self.redis)
                    retry_count = int(await redis_client.incr(retry_key) or 0)

                # 超过3次重试，则标记 分片和文件 失败
                if retry_count >= 3:
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
                            file_storage_meta_key, "status", "failed"  # Redis 中标记文件失败
                        )
                    if self.minio is not None:
                        try:
                            self.minio.remove_object(temp_bucket, chunk_object_name)  # 清理失败分片对象
                        except Exception:
                            logger.exception(
                                "清理失败分片对象失败：object_name={}",
                                chunk_object_name,
                            )
                raise

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
                    "total_size": payload.total_size,
                    "file_name": payload.file_name,
                    "content_type": payload.content_type,
                    "is_public": int(payload.is_public),
                },
            )

            # 3) 仅当 status 字段不存在时，初始化为 uploading（避免覆盖 merged）
            #    Redis 的 HSETNX: field 不存在才会写入
            await redis_client.hsetnx(file_storage_meta_key, "status", "uploading")

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
                        routing_key=settings.RABBITMQ_QUEUE,
                    )
                await redis_client.hset(file_storage_meta_key, "status", "merged")

        return {
            "file_md5": payload.file_md5,
            "chunk_index": payload.chunk_index,
            "uploaded": True,
        }

    async def _put_object_with_retry(
            self,
            *,
            temp_bucket: str,
            chunk_object_name: str,
            payload,
            chunk_bytes: bytes,
            retry_key: str,
            max_retries: int = 3,
    ) -> str:
        """
        返回: chunk_md5 (作为 etag)
        说明:
        - 在同一次请求中重试 max_retries 次
        - 每失败一次就把 Redis 的 retry_key +1
        - 超过阈值抛出最后一次异常
        """
        chunk_md5 = hashlib.md5(chunk_bytes).hexdigest()

        last_exc: Exception | None = None
        for attempt in range(1, max_retries + 1):
            try:
                self.minio.put_object(
                    bucket_name=temp_bucket,
                    object_name=chunk_object_name,
                    data=io.BytesIO(chunk_bytes),
                    length=len(chunk_bytes),
                    content_type=payload.content_type,
                )
                return chunk_md5
            except Exception as exc:
                last_exc = exc

                retry_count = attempt
                if self.redis is not None:
                    redis_client = cast(Any, self.redis)
                    retry_count = await redis_client.incr(retry_key)

                # 简单退避: 0.2s, 0.4s, 0.8s ...
                if retry_count < max_retries:
                    await asyncio.sleep(0.2 * (2 ** (retry_count - 1)))
                    continue

                raise

        raise last_exc  # 理论上到不了

    async def complete_upload(
            self,
            user: User,
            payload: FileUploadCompleteIn,
    ) -> FileStorage:
        """TODO: 合并分片并创建文件记录（业务逻辑占位）。

        说明：
        - 仅提供逻辑框架，不做具体实现

        流程（思路）：
        1. 校验 Redis bitmap 是否完整
        2. MinIO compose 合并分片
        3. 校验合并后的 file_md5
        4. 写入 file_storage，状态为 1（已上传）
        5. 清理临时桶分片
        6. 如果校验失败，标记失败并清理所有分片
        """

        if user.role != UserRole.ADMIN.value:
            payload.is_public = False

        logger.info(
            "完成上传合并（预留接口）：user_id={}, file_md5={}",
            user.id,
            payload.file_md5,
        )

        # 该接口仅作为客户端触发合并的入口，实际合并在 MQ 消费者中完成
        # 这里返回一个占位对象，后续可根据需要改为真实查询 file_storage
        return FileStorage(
            user_id=user.id,
            filename=payload.file_name,
            bucket_name="upload-final",
            object_name=f"{payload.file_md5}/{payload.file_name}",
            content_type=payload.content_type,
            file_size=payload.total_chunks,
            is_public=payload.is_public,
            status=0,
        )

    def process_file_chunks(self, file_id: int) -> None:
        """TODO: 文件分块处理（预留接口）。

        说明：
        - 这里只提供思路，不实现具体逻辑
        - 后续需要结合 MinIO/Milvus/LangChain 进行分块和向量化

        示例流程（思路）：
        1. 从 MinIO 下载文件内容
        2. 按混合策略分块（固定大小 + 语义 + 重叠）
        3. 将分块写入 file_chunks 表
        4. 调用 embedding 模型生成向量
        5. 将向量写入 Milvus，并保存 embedding_id
        """

        logger.info("开始处理文件分块（预留接口）：file_id={}", file_id)

        # TODO: 预留实现，不做任何操作
        return None
