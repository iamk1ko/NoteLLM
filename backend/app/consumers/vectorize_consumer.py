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
from app.core.settings import get_settings
from app.services.vectorization_service import VectorizationService
from app.services.vectorization.vector_store import MilvusVectorStore

logger = get_logger(__name__)


async def _vectorize_task(payload: dict[str, Any]) -> None:
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
        if task_status == "success":
            logger.info("向量化任务已完成，跳过：file_md5={}", file_md5)
            return

        settings = get_settings()
        vector_store = MilvusVectorStore(
            uri=settings.MILVUS_URI,
            collection_name=settings.VECTOR_COLLECTION,
            dim=settings.EMBEDDING_DIM,
        )

        # 确保集合已初始化 (创建或加载)
        await vector_store.init_collection()

        service = VectorizationService(
            db=db,
            redis_client=redis_client,
            minio_client=minio_client,
            vector_store=vector_store,
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
    except Exception as e:
        logger.error("向量化任务消费失败：file_md5={}, error={}", file_md5, e)
    finally:
        db.close()


async def run_vectorize_consumer() -> None:
    connection = await get_rabbitmq_connection()
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
                    await _vectorize_task(payload)
    finally:
        await channel.close()
        await connection.close()


if __name__ == "__main__":
    asyncio.run(run_vectorize_consumer())
