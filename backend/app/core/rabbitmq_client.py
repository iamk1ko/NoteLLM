from __future__ import annotations

import aio_pika
from aio_pika.abc import AbstractRobustConnection

from app.core.settings import get_settings

RABBITMQ_QUEUE_FILE_TASKS: str = "file_tasks"
RABBITMQ_QUEUE_VECTORIZE_TASKS: str = "vectorize_tasks"

# 进程内缓存连接：
# - connect_robust 本身具备自动重连能力
# - 我们在应用生命周期内尽量复用同一个 connection，避免重复握手/资源浪费
_rabbitmq_connection: AbstractRobustConnection | None = None


async def get_rabbitmq_connection() -> AbstractRobustConnection:
    """获取 RabbitMQ 异步连接（带缓存 + robust 自动重连）。

    说明：
    - 使用 aio-pika 的 connect_robust（断线后会自动重连）。
    - 这里做一层进程内单例缓存：避免每次调用都新建连接。
    - 连接信息来自 Settings.RABBITMQ_URL。

    典型用法：
    - FastAPI 启动时（lifespan）提前创建一次并缓存
    - API Depends / 后台消费者需要时再取同一个连接
    """

    global _rabbitmq_connection

    # 如果已有连接且连接仍处于打开状态，则直接复用。
    # aio-pika 的 RobustConnection 提供 is_closed 属性。
    if _rabbitmq_connection is not None and not _rabbitmq_connection.is_closed:
        return _rabbitmq_connection

    settings = get_settings()
    # register_return_callbacks=False：避免 robust connection 在关闭/重连时注册的 callback
    # 走到 pydevd_asyncio 的 ensure_future 兼容路径（其内部调用了已移除的 asyncio.tasks._wrap_awaitable）。
    _rabbitmq_connection = await aio_pika.connect_robust(
        settings.RABBITMQ_URL,
        heartbeat=30,
        register_return_callbacks=False,
    )
    return _rabbitmq_connection


async def close_rabbitmq() -> None:
    """关闭 RabbitMQ 连接（应用关停时调用）。"""

    global _rabbitmq_connection
    if _rabbitmq_connection is not None and not _rabbitmq_connection.is_closed:
        await _rabbitmq_connection.close()
    _rabbitmq_connection = None


async def get_rabbitmq_queue_name() -> str:
    """获取默认 RabbitMQ 队列名。"""

    return RABBITMQ_QUEUE_FILE_TASKS
