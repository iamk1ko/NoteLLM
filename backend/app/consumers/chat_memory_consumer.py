from __future__ import annotations

import asyncio
from typing import Any

from aio_pika.abc import AbstractIncomingMessage

from app.consumers.mq_utils import (
    declare_retry_topology,
    handle_with_retry,
    normalize_backoff_seconds,
)
from app.core.logging import get_logger
from app.core.minio_client import get_minio_client
from app.core.rabbitmq_client import (
    RABBITMQ_QUEUE_CHAT_MEMORY_TASKS,
    get_rabbitmq_connection,
)
from app.core.settings import get_settings
from app.prompts import load_prompt
from app.services.llm.service import LLMService
from app.services.memory.markdown_memory import MarkdownMemoryService

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


async def _update_memory(payload: dict[str, Any]) -> None:
    """
    TODO: 目前这个函数的功能还比较简单，并非一个实时的“记忆更新”，而是一个基于用户输入和 AI 回复的“记忆总结”。后续可以逐步增强它的功能，例如：
        - 目前它只是简单地把用户输入和 AI 回复一起总结成一个新的记忆文本，但未来可以设计成一个更智能的“记忆管理器”，它可以根据对话的上下文和历史，智能地决定哪些信息需要被保留、更新或删除，而不仅仅是简单地总结。
        - 目前它的输入是用户消息和 AI回复的文本，但未来可以扩展它的输入，包含更多的上下文信息，例如用户的情绪状态、对话的意图、相关的外部事件等，这些都可以帮助它更准确地更新记忆。
        - 目前它的输出是一个新的记忆文本，但未来可以设计成一个更结构化的记忆对象，包含不同类型的信息（例如事实、观点、情感等），并且可以支持更复杂的查询和推理功能。
    """
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

    logger.info("(该功能目前还在测试阶段, 为后期 Agent 做准备) LLM 生成的记忆更新如下：\n"
                "--------- 分割线 ---------\n"
                "{}\n"
                "-------------------------", summary_text)

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
