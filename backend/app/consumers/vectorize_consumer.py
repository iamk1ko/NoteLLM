from __future__ import annotations

import asyncio
import json
from typing import Any, cast

from app.core.db import SessionLocal
from app.core.logging import get_logger
from app.core.minio_client import get_minio_client
from app.core.rabbitmq_client import (
    RABBITMQ_QUEUE_VECTORIZE_TASKS,
    get_rabbitmq_connection,
)
from app.core.redis_client import get_redis_client, FILE_VECTORIZATION_KEY
from app.services.vectorization_service import VectorizationService

logger = get_logger(__name__)


async def _vectorize_task(payload: dict[str, Any]) -> None:
    db = SessionLocal()
    redis_client = cast(Any, get_redis_client())
    minio_client = get_minio_client()
    try:
        file_id = int(payload["file_id"])
        file_md5 = payload["file_md5"]
        bucket_name = payload["bucket_name"]
        object_name = payload["object_name"]
        content_type = payload.get("content_type") or ""

        task_key = FILE_VECTORIZATION_KEY.format(file_md5)
        task_status = await redis_client.get(task_key)
        if task_status == "success":
            logger.info("向量化任务已完成，跳过：file_md5={}", file_md5)
            return

        service = VectorizationService(
            db=db,
            redis_client=redis_client,
            minio_client=minio_client,
        )
        await service.vectorize_file(
            file_id=file_id,
            file_md5=file_md5,
            bucket_name=bucket_name,
            object_name=object_name,
            content_type=content_type,
        )
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
