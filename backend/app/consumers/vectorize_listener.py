from __future__ import annotations

"""向量化任务的 RabbitMQ 后台监听器。

设计目标与 `file_merge_listener.py` 一致：
- 应用（FastAPI）启动后自动在后台消费队列；
- 不在 import 阶段创建连接；
- 连接从 `app.state.infra.rabbitmq` 获取；
- 支持优雅停止（shutdown 时 cancel task）。

使用方式：
- 在 `main.py` 的 lifespan 里调用：
    from app.consumers.vectorize_listener import start_vectorize_listener
    vectorize_task = start_vectorize_listener(app)
  并在 shutdown 时 cancel。
"""

import asyncio
import json
from typing import Any, cast

from aio_pika.abc import AbstractIncomingMessage
from fastapi import FastAPI

from app.core.app_state import get_app_state
from app.core.logging import get_logger
from app.core.rabbitmq_client import RABBITMQ_QUEUE_VECTORIZE_TASKS
from app.core.db import get_sessionmaker
from app.core.minio_client import get_minio_client
from app.core.redis_client import get_redis_client
from app.core.constants import RedisKey
from app.core.settings import get_settings
from app.services.vectorization_service import VectorizationService
from app.services.vectorization.task_state import TaskStateStore
from app.services.vectorization.vector_store import MilvusVectorStore

logger = get_logger(__name__)


async def _vectorize_task(
    payload: dict[str, Any], milvus_store: MilvusVectorStore
) -> None:
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


async def _handle_message(
    message: AbstractIncomingMessage, milvus_store: MilvusVectorStore
) -> None:
    async with message.process():
        payload: dict[str, Any] = json.loads(message.body.decode("utf-8"))
        await _vectorize_task(payload, milvus_store)


async def _consume_loop(app: FastAPI) -> None:
    state = get_app_state(app)
    infra = state.infra
    if infra is None or infra.rabbitmq is None or infra.milvus is None:
        logger.warning("RabbitMQ 或 Milvus 未初始化，向量化监听器不会启动")
        return

    connection = infra.rabbitmq
    milvus_store = infra.milvus
    channel = await connection.channel()
    try:
        queue = await channel.declare_queue(
            RABBITMQ_QUEUE_VECTORIZE_TASKS, durable=True
        )
        logger.info(
            "向量化监听器已启动，开始消费队列：{}", RABBITMQ_QUEUE_VECTORIZE_TASKS
        )

        async with queue.iterator() as queue_iter:
            try:
                async for message in queue_iter:
                    await _handle_message(message, milvus_store)
            except asyncio.CancelledError:
                logger.info("向量化监听器收到取消信号，准备退出")
                raise
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("向量化监听器异常退出")
    finally:
        try:
            await channel.close()
        except Exception:
            pass


def start_vectorize_listener(app: FastAPI) -> asyncio.Task[None]:
    logger.info("正在启动向量化监听器...")
    return asyncio.create_task(_consume_loop(app), name="vectorize_listener")
