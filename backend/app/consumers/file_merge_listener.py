from __future__ import annotations

"""文件分片合并的 RabbitMQ 后台监听器。

目标：
- 类似 Spring Boot 的 @RabbitListener：应用启动后自动在后台消费队列。
- 不需要手动运行一个单独的 main 方法（除非你想做成独立 worker 进程）。

设计要点：
1) 监听器只负责“消费消息 + 调用业务处理函数”，不要在 import 阶段创建连接。
2) 连接从 app.state.infra.rabbitmq 获取（由 lifespan 启动时初始化）。
3) 支持优雅停止：应用 shutdown 时取消任务。

使用方式：
- 在 main.py 的 lifespan 里调用：
    from app.consumers.file_merge_listener import start_file_merge_listener
    listener_task = start_file_merge_listener(app)
  并在 shutdown 时 cancel。
"""

import asyncio
from typing import Any
from fastapi import FastAPI
from aio_pika.abc import AbstractIncomingMessage

from app.core.logging import get_logger
from app.core.rabbitmq_client import RABBITMQ_QUEUE_FILE_TASKS
from app.core.settings import get_settings
from app.consumers.file_merge_consumer import _merge_file
from app.core.app_state import get_app_state
from app.consumers.mq_utils import (
    declare_retry_topology,
    handle_with_retry,
    normalize_backoff_seconds,
)

logger = get_logger(__name__)


async def _consume_loop(app: FastAPI) -> None:
    """消费循环：持续监听队列并处理消息。

    注意：
    - 这里不做连接创建，连接来自 app.state.infra。
    - shutdown 时任务会被 cancel，此时 aio-pika 可能在等待消息（__anext__）中抛 CancelledError。
      这属于“正常退出路径”，必须捕获并吞掉，否则 FastAPI 会认为 shutdown 失败。
    """

    state = get_app_state(app)
    infra = state.infra
    if infra is None or infra.rabbitmq is None:
        logger.warning("RabbitMQ 未初始化，文件合并监听器不会启动")
        return

    connection = infra.rabbitmq
    channel = await connection.channel()
    try:
        settings = get_settings()
        backoff_seconds = normalize_backoff_seconds(settings.MQ_RETRY_BACKOFF_SECONDS)
        retry_ttl_ms_list = [s * 1000 for s in backoff_seconds]
        topology = await declare_retry_topology(
            channel,
            RABBITMQ_QUEUE_FILE_TASKS,
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
        logger.info("文件合并监听器已启动，开始消费队列：{}", topology.queue_name)

        async with queue.iterator() as queue_iter:
            try:
                async for message in queue_iter:
                    await _handle_message(message, topology)
            except asyncio.CancelledError:
                # 正常：应用关闭时取消任务
                logger.info("文件合并监听器收到取消信号，准备退出")
                raise
    except asyncio.CancelledError:
        # 注意：这里重新抛出，让外层（lifespan）统一 await 时捕获取消异常；
        # 外层会吞掉 CancelledError，从而避免被 FastAPI 判定为 shutdown 失败。
        raise
    except Exception:
        # 任何非预期异常：记录后退出（一般也可以设计成 sleep 重试）
        logger.exception("文件合并监听器异常退出")
    finally:
        # 优雅关闭 channel（connection 由 InfraProvider 管理）
        try:
            await channel.close()
        except Exception:
            pass


async def _handle_message(message: AbstractIncomingMessage, topology) -> None:
    """处理单条 RabbitMQ 消息。"""

    async def handler(payload: dict[str, Any]) -> None:
        await _merge_file(payload["file_md5"], payload["user_id"])

    settings = get_settings()
    await handle_with_retry(
        message,
        queue_name=RABBITMQ_QUEUE_FILE_TASKS,
        handler=handler,
        topology=topology,
        max_retries=settings.MQ_RETRY_MAX_ATTEMPTS,
    )


def start_file_merge_listener(app: FastAPI) -> asyncio.Task[None]:
    """启动后台监听任务并返回 task 句柄。"""

    return asyncio.create_task(_consume_loop(app), name="file_merge_listener")
