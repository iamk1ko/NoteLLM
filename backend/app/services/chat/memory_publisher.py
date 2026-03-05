from __future__ import annotations

import json

import aio_pika

from app.core.logging import get_logger
from app.core.rabbitmq_client import (
    RABBITMQ_QUEUE_CHAT_MEMORY_TASKS,
    get_rabbitmq_connection,
)

logger = get_logger(__name__)


class MemoryUpdatePublisher:
    async def enqueue(
        self, user_id: int, session_id: int, user_message: str, ai_response: str
    ) -> None:
        try:
            connection = await get_rabbitmq_connection()
            channel = await connection.channel()
            try:
                payload = {
                    "user_id": user_id,
                    "session_id": session_id,
                    "user_message": user_message,
                    "ai_response": ai_response,
                }
                await channel.default_exchange.publish(
                    aio_pika.Message(
                        body=json.dumps(payload, ensure_ascii=False).encode("utf-8")
                    ),
                    routing_key=RABBITMQ_QUEUE_CHAT_MEMORY_TASKS,
                )
            finally:
                await channel.close()
        except Exception as e:
            logger.error("长期记忆任务投递失败: {}", e)
