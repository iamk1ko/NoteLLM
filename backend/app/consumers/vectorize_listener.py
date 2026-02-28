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
from typing import Any

from aio_pika.abc import AbstractIncomingMessage
from fastapi import FastAPI

from app.core.app_state import get_app_state
from app.core.logging import get_logger
from app.core.rabbitmq_client import RABBITMQ_QUEUE_VECTORIZE_TASKS
from app.core.settings import get_settings
from app.consumers.mq_utils import (
    declare_retry_topology,
    handle_with_retry,
    normalize_backoff_seconds,
)
from app.services.vectorization.vector_store import MilvusVectorStore
from app.consumers.vectorize_consumer import _vectorize_task

logger = get_logger(__name__)


async def _handle_message(
        message: AbstractIncomingMessage, milvus_store: MilvusVectorStore, topology
) -> None:
    async def handler(payload: dict[str, Any]) -> None:
        await _vectorize_task(payload, milvus_store)

    settings = get_settings()
    await handle_with_retry(
        message,
        queue_name=RABBITMQ_QUEUE_VECTORIZE_TASKS,
        handler=handler,
        topology=topology,
        max_retries=settings.MQ_RETRY_MAX_ATTEMPTS,
    )


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
        settings = get_settings()
        backoff_seconds = normalize_backoff_seconds(settings.MQ_RETRY_BACKOFF_SECONDS)
        retry_ttl_ms_list = [s * 1000 for s in backoff_seconds]
        topology = await declare_retry_topology(
            channel,
            RABBITMQ_QUEUE_VECTORIZE_TASKS,
            retry_ttl_ms_list=retry_ttl_ms_list,
        )

        # 拿到 Queue 对象用于消费（不要额外传 arguments，避免与 declare_retry_topology 的声明不一致）
        queue = await channel.declare_queue(topology.queue_name, durable=True)
        logger.info("向量化监听器已启动，开始消费队列：{}", topology.queue_name)

        async with queue.iterator() as queue_iter:
            try:
                async for message in queue_iter:
                    await _handle_message(message, milvus_store, topology)
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
