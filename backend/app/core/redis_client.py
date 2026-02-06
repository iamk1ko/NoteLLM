from __future__ import annotations

import redis.asyncio as redis
from redis.asyncio import Redis

from app.core.settings import get_settings


def get_redis_client() -> Redis:
    """创建 Redis 异步客户端对象。

    说明（很关键）：
    - 这个函数只是“构造客户端对象/连接池配置”，通常不会在这里立刻发起网络连接。
    - 真实的网络连接一般发生在你第一次执行命令时（比如 `await client.ping()`）。
    - 因此它是“无副作用”的，适合在 lifespan 中创建并缓存。

    连接信息来自：Settings.REDIS_URL
    """

    settings = get_settings()
    return redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        max_connections=settings.REDIS_MAX_CONNECTIONS,
    )
