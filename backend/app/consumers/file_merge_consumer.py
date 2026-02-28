from __future__ import annotations

import asyncio
import hashlib
import json
from typing import Any, cast

from minio.commonconfig import ComposeSource
import aio_pika

from app.core.logging import get_logger
from app.core.minio_client import get_minio_client, get_file_buckets
from app.core.redis_client import get_redis_client
from app.core.constants import RedisKey
from app.core.rabbitmq_client import (
    get_rabbitmq_connection,
    RABBITMQ_QUEUE_FILE_TASKS,
    RABBITMQ_QUEUE_VECTORIZE_TASKS,
)
from app.core.db import get_sessionmaker

from app.crud import FileStorageCRUD, FileChunksCRUD
from app.models import FileStorageStatus

logger = get_logger(__name__)


async def _merge_file(file_md5: str, user_id: int) -> None:
    """合并分片并更新数据库状态。

    说明：
    - 读取所有分片
    - MinIO compose 合并
    - 校验 MD5
    - 更新 file_storage 状态
    - 删除分片记录与临时对象

    注意：
    - 这里会按需创建 Redis/MinIO 客户端对象（对象创建本身通常不发起网络连接）。
    - 真正的网络 I/O 在调用 ping/bucket_exists/compose_object 等方法时发生。
    """

    redis_client = cast(Any, get_redis_client())
    minio_client = get_minio_client()
    temp_bucket, final_bucket = get_file_buckets()

    db = get_sessionmaker()()
    try:
        chunks = FileChunksCRUD.list_chunks(db, file_md5)
        if not chunks:
            logger.warning("未找到分片记录：file_md5={}", file_md5)
            return

        # 从 Redis meta 中获取文件名
        meta_key = RedisKey.FILE_STORAGE_METADATA.format(user_id, file_md5)
        file_name = await redis_client.hget(meta_key, "file_name")
        if not file_name:
            logger.error("无法获取文件名：file_md5={}", file_md5)
            return
        if isinstance(file_name, (bytes, bytearray)):
            file_name = file_name.decode("utf-8")

        source_object_name = f"{file_md5}/{file_name}"
        object_name = source_object_name

        # MinIO compose 合并
        sources = [ComposeSource(temp_bucket, c.object_name) for c in chunks]
        minio_client.compose_object(final_bucket, object_name, sources)

        # 校验 MD5（注意：这里会读取整个对象到内存，适合小文件；大文件建议流式校验）
        obj = minio_client.get_object(final_bucket, object_name)
        file_md5_actual = hashlib.md5(obj.read()).hexdigest()
        obj.close()
        obj.release_conn()

        file_obj = FileStorageCRUD.get_file_by_object_name(
            db, user_id, source_object_name
        )

        if file_md5_actual != file_md5:
            logger.error(
                "MD5 校验失败：file_md5={}, actual={}", file_md5, file_md5_actual
            )
            if file_obj:
                FileStorageCRUD.update_file_status(
                    db, file_id=file_obj.id, status=FileStorageStatus.FAILED.value
                )
            # 清理 MinIO 中存储的临时分片
            for chunk in chunks:
                minio_client.remove_object(temp_bucket, chunk.object_name)
            return

        # 更新 file_storage 状态
        if file_obj:
            FileStorageCRUD.update_file_upload_complete(
                db,
                file_id=file_obj.id,
                bucket_name=final_bucket,
                object_name=object_name,
                status=FileStorageStatus.UPLOADED.value,
            )

            connection = await get_rabbitmq_connection()
            channel = await connection.channel()
            try:
                await channel.default_exchange.publish(
                    aio_pika.Message(
                        # TODO: 这里 Redis 中的 meta 信息还未被删除，消息内容其实可以更简洁一些；
                        #  但为了后续可能的扩展（比如向量化任务可能需要更多信息），暂时保持完整。
                        body=json.dumps(
                            {
                                "file_id": file_obj.id,
                                "file_md5": file_md5,
                                "bucket_name": final_bucket,
                                "object_name": object_name,
                                "content_type": file_obj.content_type,
                                "user_id": user_id,
                            },
                            ensure_ascii=False,
                        ).encode("utf-8")
                    ),
                    routing_key=RABBITMQ_QUEUE_VECTORIZE_TASKS,
                )
            finally:
                await channel.close()

        # 清理 MinIO 中存储的临时分片
        for chunk in chunks:
            minio_client.remove_object(temp_bucket, chunk.object_name)
        logger.info("合并完成：file_md5={}", file_md5)
    finally:
        # 删除分片记录（不管合并成功与否，都清理 DB 中的分片记录）
        FileChunksCRUD.delete_chunks(db, file_md5)

        # 清理 Redis 中分片相关的元信息（如果有的话）
        await redis_client.delete(
            RedisKey.UPLOAD_FILE_CHUNKS_BITMAP.format(user_id, file_md5)
        )
        await redis_client.delete(
            RedisKey.FILE_STORAGE_METADATA.format(user_id, file_md5)
        )
        logger.debug("已清理临时分片数据：file_md5={}", file_md5)
        db.close()


async def run_file_merge_consumer() -> None:
    """作为“独立 worker”运行的 RabbitMQ 消费者入口。

    说明：
    - 与 `file_merge_listener.py` 不同，这里是独立进程模式。
    - 适合生产：把 web 服务与 consumer 解耦，避免多 worker 时重复消费。
    """

    connection = await get_rabbitmq_connection()
    channel = await connection.channel()
    try:
        queue = await channel.declare_queue(RABBITMQ_QUEUE_FILE_TASKS, durable=True)
        logger.info(
            "file_merge_consumer(worker) 已启动，开始消费队列：{}",
            RABBITMQ_QUEUE_FILE_TASKS,
        )

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    payload = json.loads(message.body.decode("utf-8"))
                    await _merge_file(payload["file_md5"], payload["user_id"])
    finally:
        await channel.close()
        # connection 使用的是 robust + 缓存连接；如果你希望独立 worker 退出就关闭连接，可以直接 close。
        await connection.close()


if __name__ == "__main__":
    asyncio.run(run_file_merge_consumer())
