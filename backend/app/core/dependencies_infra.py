from __future__ import annotations

from typing import AsyncGenerator

from fastapi import Request, HTTPException
from minio import Minio
from redis.asyncio import Redis
from aio_pika.abc import AbstractRobustConnection, AbstractChannel


def get_redis(request: Request) -> Redis:
    """获取 Redis 客户端（依赖注入）。

    说明：
    - 客户端在 lifespan 中初始化并挂载到 app.state
    - 这里仅取出并返回
    """

    redis_client = getattr(request.app.state, "redis", None)
    if redis_client is None:
        raise HTTPException(status_code=503, detail="Redis 客户端未初始化")
    return redis_client


def get_minio(request: Request) -> Minio:
    """获取 MinIO 客户端（依赖注入）。"""

    minio_client = getattr(request.app.state, "minio", None)
    if minio_client is None:
        raise HTTPException(status_code=503, detail="MinIO 客户端未初始化")
    return minio_client


def get_rabbitmq_connection(request: Request) -> AbstractRobustConnection:
    """获取 RabbitMQ 连接（依赖注入）。"""

    rabbitmq = getattr(request.app.state, "rabbitmq", None)
    if rabbitmq is None:
        raise HTTPException(status_code=503, detail="RabbitMQ 客户端未初始化")
    return rabbitmq


async def get_rabbitmq_channel(
    request: Request,
) -> AsyncGenerator[AbstractChannel, None]:
    """获取 RabbitMQ Channel（依赖注入）。

    说明：
    - 每次请求创建一个 channel
    - 使用完毕后自动关闭
    """

    connection: AbstractRobustConnection = request.app.state.rabbitmq
    channel = await connection.channel()
    try:
        yield channel
    finally:
        await channel.close()
