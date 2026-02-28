from __future__ import annotations

"""聊天长期记忆任务的 RabbitMQ 后台监听器。"""

import asyncio
import json
from typing import Any

from aio_pika.abc import AbstractIncomingMessage
from fastapi import FastAPI

from app.core.app_state import get_app_state
from app.core.logging import get_logger
from app.core.rabbitmq_client import (
    RABBITMQ_QUEUE_CHAT_MEMORY_TASKS,
    RABBITMQ_QUEUE_CHAT_MEMORY_RETRY_TASKS,
    RABBITMQ_QUEUE_CHAT_MEMORY_DLQ,
)
from app.consumers.chat_memory_consumer import _update_memory

logger = get_logger(__name__)


async def _handle_message(message: AbstractIncomingMessage) -> None:
    async with message.process():
        payload: dict[str, Any] = json.loads(message.body.decode("utf-8"))
        await _update_memory(payload)


async def _consume_loop(app: FastAPI) -> None:
    state = get_app_state(app)
    infra = state.infra
    if infra is None or infra.rabbitmq is None:
        logger.warning("RabbitMQ 未初始化，聊天记忆监听器不会启动")
        return

    connection = infra.rabbitmq
    channel = await connection.channel()
    try:
        await channel.declare_queue(RABBITMQ_QUEUE_CHAT_MEMORY_TASKS, durable=True)
        await channel.declare_queue(
            RABBITMQ_QUEUE_CHAT_MEMORY_RETRY_TASKS, durable=True
        )
        await channel.declare_queue(RABBITMQ_QUEUE_CHAT_MEMORY_DLQ, durable=True)
        queue = await channel.declare_queue(
            RABBITMQ_QUEUE_CHAT_MEMORY_TASKS, durable=True
        )
        logger.info(
            "聊天记忆监听器已启动，开始消费队列：{}", RABBITMQ_QUEUE_CHAT_MEMORY_TASKS
        )

        async with queue.iterator() as queue_iter:
            try:
                async for message in queue_iter:
                    await _handle_message(message)
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
