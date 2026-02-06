from __future__ import annotations

import aio_pika
from aio_pika.abc import AbstractRobustConnection

from app.core.settings import get_settings

RABBITMQ_QUEUE_FILE_TASKS: str = "file_tasks"


async def get_rabbitmq_connection() -> AbstractRobustConnection:
    """获取 RabbitMQ 异步连接。

    说明：
    - 使用 aio-pika 的 connect_robust
    - 连接信息来自 Settings.RABBITMQ_URL
    """

    settings = get_settings()
    return await aio_pika.connect_robust(settings.RABBITMQ_URL)


async def get_rabbitmq_queue_name() -> str:
    """获取默认 RabbitMQ 队列名。

    说明：
    - 从 Settings 读取 RABBITMQ_QUEUE
    - 统一用于文件处理任务
    """

    return RABBITMQ_QUEUE_FILE_TASKS
