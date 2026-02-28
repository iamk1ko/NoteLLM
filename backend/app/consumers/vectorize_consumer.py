from __future__ import annotations

import asyncio
import json
from typing import Any, cast

from app.core.constants import RedisKey
from app.core.db import get_sessionmaker
from app.core.logging import get_logger
from app.core.minio_client import get_minio_client
from app.core.providers import InfraProvider
from app.core.rabbitmq_client import (
    RABBITMQ_QUEUE_VECTORIZE_TASKS,
)
from app.core.redis_client import get_redis_client
from app.core.settings import get_settings
from app.services import MilvusVectorStore
from app.services.vectorization.task_state import TaskStateStore
from app.services.vectorization_service import VectorizationService

logger = get_logger(__name__)


async def _vectorize_task(payload: dict[str, Any], milvus_store: MilvusVectorStore) -> None:
    """执行单条向量化任务。"""

    db = get_sessionmaker()()
    redis_client = cast(Any, get_redis_client())
    minio_client = get_minio_client()
    file_md5 = "unknown"

    try:
        file_id = int(payload["file_id"])
        file_md5 = payload["file_md5"]
        bucket_name = payload["bucket_name"]
        object_name = payload["object_name"]
        content_type = payload.get("content_type") or ""

        task_status = await redis_client.get(
            RedisKey.FILE_VECTORIZATION_TASK_STATUS.format(file_md5)
        )
        if isinstance(task_status, (bytes, bytearray)):
            task_status = task_status.decode("utf-8")
        if task_status == "success":
            logger.info("Redis 显示向量化成功，清理后重跑：file_md5={}", file_md5)
            await TaskStateStore(redis_client).clear(file_md5)

        settings = get_settings()

        # 使用传入的 milvus_store，假设已在应用启动时初始化完成
        service = VectorizationService(
            db=db,
            redis_client=redis_client,
            minio_client=minio_client,
            vector_store=milvus_store,
            memory_threshold_mb=settings.VECTOR_MEMORY_THRESHOLD_MB,
            vector_batch_size=settings.VECTOR_BATCH_SIZE,
        )
        await service.vectorize_file(
            file_id=file_id,
            file_md5=file_md5,
            bucket_name=bucket_name,
            object_name=object_name,
            content_type=content_type,
        )
        logger.info("向量化任务完成, file_md5={}", file_md5)
    except Exception as e:
        logger.error("向量化任务消费失败：file_md5={}, error={}", file_md5, e)
    finally:
        db.close()


async def run_vectorize_consumer() -> None:
    infra = InfraProvider()
    await infra.init()
    if infra.rabbitmq is None or infra.milvus is None:
        logger.error("向量化消费者启动失败：RabbitMQ 或 Milvus 未初始化")
        return

    connection = infra.rabbitmq
    channel = await connection.channel()
    try:
        queue = await channel.declare_queue(
            RABBITMQ_QUEUE_VECTORIZE_TASKS, durable=True
        )
        logger.info(
            "vectorize_consumer(worker) 已启动，开始消费队列：{}",
            RABBITMQ_QUEUE_VECTORIZE_TASKS,
        )

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    payload = json.loads(message.body.decode("utf-8"))
                    await _vectorize_task(payload, infra.milvus)
    finally:
        await channel.close()
        await infra.close()


if __name__ == "__main__":
    asyncio.run(run_vectorize_consumer())
