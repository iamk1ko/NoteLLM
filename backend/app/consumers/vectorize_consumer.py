from __future__ import annotations

import asyncio
import json
from typing import Any, cast

from app.core.db import get_sessionmaker
from app.core.logging import get_logger
from app.core.minio_client import get_minio_client
from app.core.rabbitmq_client import (
    RABBITMQ_QUEUE_VECTORIZE_TASKS,
    get_rabbitmq_connection,
)
from app.core.redis_client import get_redis_client
from app.core.constants import RedisKey
from app.services.vectorization_service import VectorizationService
from app.services.vectorization.task_state import TaskStateStore
from app.core.settings import get_settings
from app.core.providers import InfraProvider

logger = get_logger(__name__)


async def _vectorize_task(payload: dict[str, Any], milvus_store) -> None:
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

        vector_store = milvus_store

        service = VectorizationService(
            db=db,
            redis_client=redis_client,
            minio_client=minio_client,
            vector_store=vector_store,
            memory_threshold_mb=get_settings().VECTOR_MEMORY_THRESHOLD_MB,
            vector_batch_size=get_settings().VECTOR_BATCH_SIZE,
        )
        await service.vectorize_file(
            file_id=file_id,
            file_md5=file_md5,
            bucket_name=bucket_name,
            object_name=object_name,
            content_type=content_type,
        )
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
