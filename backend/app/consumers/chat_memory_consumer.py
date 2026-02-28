from __future__ import annotations

import asyncio
from typing import Any

from aio_pika.abc import AbstractIncomingMessage

from app.utils.mq_utils import declare_retry_topology, handle_with_retry
from app.core.logging import get_logger
from app.core.rabbitmq_client import (
    RABBITMQ_QUEUE_CHAT_MEMORY_TASKS,
    get_rabbitmq_connection,
)
from app.core.settings import get_settings
from app.core.minio_client import get_minio_client
from app.prompts import load_prompt
from app.services.llm.service import LLMService
from app.services.memory.markdown_memory import MarkdownMemoryService

logger = get_logger(__name__)


async def _handle_message(message: AbstractIncomingMessage, topology) -> None:
    await handle_with_retry(
        message,
        queue_name=RABBITMQ_QUEUE_CHAT_MEMORY_TASKS,
        handler=_update_memory,  # 实际处理函数作为参数传入。注意：handler函数只能接受payload参数!!!
        topology=topology,
        max_retries=3,
    )


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


def _parse_summary_updates(content: str) -> dict[str, str]:
    sections: dict[str, str] = {
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
        topology = await declare_retry_topology(
            channel, RABBITMQ_QUEUE_CHAT_MEMORY_TASKS, retry_ttl_ms=30000
        )
        # 拿到 Queue 对象用于消费（不要额外传 arguments，避免与 declare_retry_topology 的声明不一致）
        queue = await channel.declare_queue(topology.queue_name, durable=True)
        logger.info(
            "chat_memory_consumer(worker) 已启动，开始消费队列：{}",
            RABBITMQ_QUEUE_CHAT_MEMORY_TASKS,
        )

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                await _handle_message(message, topology)
    finally:
        await channel.close()
        await connection.close()


if __name__ == "__main__":
    asyncio.run(run_chat_memory_consumer())
