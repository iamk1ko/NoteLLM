from __future__ import annotations

from typing import Any, cast

from redis.asyncio import Redis

from app.core.redis_client import FILE_VECTORIZATION_TASK_STATUS


class TaskStateStore:
    def __init__(self, redis_client: Redis | None):
        self.redis = redis_client

    async def get_status(self, file_md5: str) -> str | None:
        if self.redis is None:
            return None
        redis_client = cast(Any, self.redis)
        return await redis_client.get(FILE_VECTORIZATION_TASK_STATUS.format(file_md5))

    async def set_status(self, file_md5: str, status: str) -> None:
        if self.redis is None:
            return
        redis_client = cast(Any, self.redis)
        await redis_client.set(FILE_VECTORIZATION_TASK_STATUS.format(file_md5), status)

    async def get_cursor(self, file_md5: str) -> str | None:
        if self.redis is None:
            return None
        redis_client = cast(Any, self.redis)
        return await redis_client.get(f"vector:cursor:{file_md5}")

    async def set_cursor(self, file_md5: str, cursor: str) -> None:
        if self.redis is None:
            return
        redis_client = cast(Any, self.redis)
        await redis_client.set(f"vector:cursor:{file_md5}", cursor)
