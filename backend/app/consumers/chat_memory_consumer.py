from __future__ import annotations

import asyncio
import json
from typing import Any

from aio_pika import Message
from aio_pika.abc import AbstractIncomingMessage

from app.core.logging import get_logger
from app.core.rabbitmq_client import (
    RABBITMQ_QUEUE_CHAT_MEMORY_TASKS,
    RABBITMQ_QUEUE_CHAT_MEMORY_RETRY_TASKS,
    RABBITMQ_QUEUE_CHAT_MEMORY_DLQ,
    get_rabbitmq_connection,
)
from app.core.settings import get_settings
from app.prompts import load_prompt
from app.services.llm.service import LLMService
from app.services.memory.markdown_memory import MarkdownMemoryService
from app.core.minio_client import get_minio_client

logger = get_logger(__name__)


async def _handle_message(message: AbstractIncomingMessage) -> None:
    try:
        payload: dict[str, Any] = json.loads(message.body.decode("utf-8"))
        await _update_memory(payload)
        await message.ack()
    except Exception as e:
        await _handle_failure(message, e)


async def _update_memory(payload: dict[str, Any]) -> None:
    user_id = int(payload["user_id"])
    session_id = int(payload["session_id"])
    user_message = payload.get("user_message", "")
    ai_response = payload.get("ai_response", "")

    settings = get_settings()
    llm = LLMService(
        api_key=settings.BLSC_API_KEY or "",
        base_url=settings.BLSC_BASE_URL or "",
        model=settings.LLM_MODEL,
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
    )

    prompt = load_prompt("memory_update.txt").format(
        user_message=user_message,
        assistant_message=ai_response,
    )

    summary_text = await llm.chat(
        [
            {"role": "system", "content": load_prompt("chat_system.txt")},
            {"role": "user", "content": prompt},
        ]
    )

    updates = _parse_summary_updates(summary_text)
    memory = MarkdownMemoryService(get_minio_client())
    await memory.apply_updates(user_id, session_id, updates)


async def _handle_failure(message: AbstractIncomingMessage, error: Exception) -> None:
    headers = message.headers or {}
    retry_count = int(headers.get("x-retry-count", 0))
    body = message.body

    connection = await get_rabbitmq_connection()
    channel = await connection.channel()
    try:
        if retry_count < 3:
            next_headers = {**headers, "x-retry-count": retry_count + 1}
            await channel.default_exchange.publish(
                Message(body=body, headers=next_headers),
                routing_key=RABBITMQ_QUEUE_CHAT_MEMORY_RETRY_TASKS,
            )
            logger.warning(
                "聊天记忆消费失败，投递重试队列: retry_count={}, error={}",
                retry_count + 1,
                error,
            )
        else:
            await channel.default_exchange.publish(
                Message(body=body, headers=headers),
                routing_key=RABBITMQ_QUEUE_CHAT_MEMORY_DLQ,
            )
            logger.error(
                "聊天记忆消费失败，投递死信队列: retry_count={}, error={}",
                retry_count,
                error,
            )
    finally:
        await channel.close()
    await message.ack()


def _parse_summary_updates(content: str) -> dict[str, str]:
    sections = {
        "role_policies": "",
        "task": "",
        "state": "",
        "output": "",
    }
    if not content:
        return sections

    current_key = ""
    for line in content.split("\n"):
        header = line.strip().lower()
        if header.startswith("role"):
            current_key = "role_policies"
            continue
        if header.startswith("task"):
            current_key = "task"
            continue
        if header.startswith("state"):
            current_key = "state"
            continue
        if header.startswith("output"):
            current_key = "output"
            continue
        if current_key:
            sections[current_key] += line + "\n"

    return {k: v.strip() for k, v in sections.items()}


async def run_chat_memory_consumer() -> None:
    connection = await get_rabbitmq_connection()
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
            "chat_memory_consumer(worker) 已启动，开始消费队列：{}",
            RABBITMQ_QUEUE_CHAT_MEMORY_TASKS,
        )

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                await _handle_message(message)
    finally:
        await channel.close()
        await connection.close()


if __name__ == "__main__":
    asyncio.run(run_chat_memory_consumer())
