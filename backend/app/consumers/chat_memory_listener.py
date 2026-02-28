from __future__ import annotations

"""聊天长期记忆任务的 RabbitMQ 后台监听器。"""

import asyncio
from aio_pika.abc import AbstractIncomingMessage
from fastapi import FastAPI

from app.core.app_state import get_app_state
from app.core.logging import get_logger
from app.core.rabbitmq_client import RABBITMQ_QUEUE_CHAT_MEMORY_TASKS
from app.consumers.chat_memory_consumer import _update_memory
from app.utils.mq_utils import declare_retry_topology, handle_with_retry

logger = get_logger(__name__)


async def _handle_message(message: AbstractIncomingMessage, topology) -> None:
    await handle_with_retry(
        message,
        queue_name=RABBITMQ_QUEUE_CHAT_MEMORY_TASKS,
        handler=_update_memory,
        topology=topology,
        max_retries=3,
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
        topology = await declare_retry_topology(channel, RABBITMQ_QUEUE_CHAT_MEMORY_TASKS, retry_ttl_ms=30000)

        # 为了拿到 Queue 对象进行消费，这里再 declare 一次同名主队列。
        # 注意：如果队列已存在，RabbitMQ 要求声明参数与已有队列一致；
        # 因此这里不要额外传 arguments，避免与 declare_retry_topology 里带 arguments 的声明产生冲突。
        queue = await channel.declare_queue(topology.queue_name, durable=True)
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
