from __future__ import annotations

import redis.asyncio as redis
from redis.asyncio import Redis

from app.core.settings import get_settings


def get_redis_client() -> Redis:
    """获取 Redis 异步客户端。

    说明：
    - 使用 redis.asyncio
    - 连接信息来自 Settings.REDIS_URL
    """

    settings = get_settings()
    return redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        max_connections=settings.REDIS_MAX_CONNECTIONS,
    )
