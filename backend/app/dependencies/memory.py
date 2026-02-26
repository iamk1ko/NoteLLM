from __future__ import annotations

from typing import Callable

from minio import Minio
from fastapi import Depends
from redis.asyncio import Redis

from app.dependencies.infra import get_redis, get_minio
from app.services.memory.markdown_memory import MarkdownMemoryService
from app.services.memory.redis_memory import RedisChatMemory


def get_redis_chat_memory(
    redis_client: Redis = Depends(get_redis),
) -> Callable[[int, int], RedisChatMemory]:
    """获取 Redis 短期记忆实例（工厂函数）"""

    def create(session_id: int, memory_limit: int = 20) -> RedisChatMemory:
        return RedisChatMemory(redis_client, session_id, memory_limit)

    return create


def get_markdown_memory(
    minio_client: Minio = Depends(get_minio),
) -> MarkdownMemoryService:
    """获取 Markdown 长期记忆服务实例"""
    return MarkdownMemoryService(minio_client)
