from __future__ import annotations

"""聊天长期记忆任务的 RabbitMQ 后台监听器。"""

import asyncio
from aio_pika.abc import AbstractIncomingMessage
from fastapi import FastAPI

from app.core.app_state import get_app_state
from app.core.logging import get_logger
from app.core.rabbitmq_client import RABBITMQ_QUEUE_CHAT_MEMORY_TASKS
from app.core.settings import get_settings
from app.consumers.chat_memory_consumer import _update_memory
from app.consumers.mq_utils import (
    declare_retry_topology,
    handle_with_retry,
    normalize_backoff_seconds,
)

logger = get_logger(__name__)


async def _handle_message(message: AbstractIncomingMessage, topology) -> None:
    settings = get_settings()
    await handle_with_retry(
        message,
        queue_name=RABBITMQ_QUEUE_CHAT_MEMORY_TASKS,
        handler=_update_memory,
        topology=topology,
        max_retries=settings.MQ_RETRY_MAX_ATTEMPTS,
    )


async def _consume_loop(app: FastAPI) -> None:
    state = get_app_state(app)
    infra = state.infra
    if infra is None or infra.rabbitmq is None:
        logger.warning("RabbitMQ 未初始化，聊天记忆监听器不会启动")
        return

    connection = infra.rabbitmq
    channel = await connection.channel()
    try:
        # 统一由 declare_retry_topology 声明：主队列(带 DLX 参数) + retry 队列 + dlq 队列 + exchange/bind
        settings = get_settings()
        backoff_seconds = normalize_backoff_seconds(settings.MQ_RETRY_BACKOFF_SECONDS)
        retry_ttl_ms_list = [s * 1000 for s in backoff_seconds]
        topology = await declare_retry_topology(
            channel,
            RABBITMQ_QUEUE_CHAT_MEMORY_TASKS,
            retry_ttl_ms_list=retry_ttl_ms_list,
            force_recreate=settings.MQ_FORCE_RECREATE_QUEUES,
            enable_dlq=settings.MQ_DLQ_ENABLED,
        )

        if not topology.configured:
            logger.warning("队列未启用DLX配置，跳过监听：{}", topology.queue_name)
            return
        queue = await channel.declare_queue(
            topology.queue_name, durable=True, arguments=topology.main_queue_args
        )
        logger.info("聊天记忆监听器已启动，开始消费队列：{}", topology.queue_name)

        async with queue.iterator() as queue_iter:
            try:
                async for message in queue_iter:
                    await _handle_message(message, topology)
            except asyncio.CancelledError:
                logger.info("聊天记忆监听器收到取消信号，准备退出")
                raise
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("聊天记忆监听器异常退出")
    finally:
        try:
            await channel.close()
        except Exception:
            pass


def start_chat_memory_listener(app: FastAPI) -> asyncio.Task[None]:
    logger.info("正在启动聊天记忆监听器...")
    return asyncio.create_task(_consume_loop(app), name="chat_memory_listener")
