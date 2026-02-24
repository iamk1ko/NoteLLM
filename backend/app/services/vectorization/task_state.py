from __future__ import annotations

from typing import Any, cast

from redis.asyncio import Redis

import time

from app.core.constants import RedisKey
from app.core.settings import get_settings

from app.services.vectorization.errors import VectorizationError


class TaskStateStore:
    def __init__(self, redis_client: Redis | None):
        self.redis = redis_client

    async def get_status(self, file_md5: str) -> str | None:
        if self.redis is None:
            return None
        redis_client = cast(Any, self.redis)
        return await redis_client.get(
            RedisKey.FILE_VECTORIZATION_TASK_STATUS.format(file_md5)
        )

    async def set_status(self, file_md5: str, status: str) -> None:
        if self.redis is None:
            return
        redis_client = cast(Any, self.redis)
        await redis_client.set(
            RedisKey.FILE_VECTORIZATION_TASK_STATUS.format(file_md5), status
        )
        await redis_client.set(
            RedisKey.FILE_VECTORIZATION_TASK_UPDATED_AT.format(file_md5),
            int(time.time()),
        )
        await self._touch_ttl(file_md5)

    async def get_error(self, file_md5: str) -> str | None:
        if self.redis is None:
            return None
        redis_client = cast(Any, self.redis)
        return await redis_client.get(
            RedisKey.FILE_VECTORIZATION_TASK_ERROR.format(file_md5)
        )

    async def set_error(self, file_md5: str, error: str) -> None:
        if self.redis is None:
            return
        redis_client = cast(Any, self.redis)
        await redis_client.set(
            RedisKey.FILE_VECTORIZATION_TASK_ERROR.format(file_md5), error
        )
        await self._touch_ttl(file_md5)

    async def set_error_details(
        self, file_md5: str, error: VectorizationError | None
    ) -> None:
        if self.redis is None:
            return
        redis_client = cast(Any, self.redis)
        if error is None:
            await redis_client.delete(
                RedisKey.FILE_VECTORIZATION_TASK_STAGE.format(file_md5),
                RedisKey.FILE_VECTORIZATION_TASK_ERROR_CODE.format(file_md5),
                RedisKey.FILE_VECTORIZATION_TASK_ERROR_MESSAGE.format(file_md5),
                RedisKey.FILE_VECTORIZATION_TASK_RETRYABLE.format(file_md5),
            )
            await self._touch_ttl(file_md5)
            return
        await redis_client.set(
            RedisKey.FILE_VECTORIZATION_TASK_STAGE.format(file_md5),
            error.stage.value,
        )
        await redis_client.set(
            RedisKey.FILE_VECTORIZATION_TASK_ERROR_CODE.format(file_md5),
            error.code,
        )
        await redis_client.set(
            RedisKey.FILE_VECTORIZATION_TASK_ERROR_MESSAGE.format(file_md5),
            error.message,
        )
        await redis_client.set(
            RedisKey.FILE_VECTORIZATION_TASK_RETRYABLE.format(file_md5),
            "1" if error.retryable else "0",
        )
        await self._touch_ttl(file_md5)

    async def set_stage(self, file_md5: str, stage: str) -> None:
        if self.redis is None:
            return
        redis_client = cast(Any, self.redis)
        await redis_client.set(
            RedisKey.FILE_VECTORIZATION_TASK_STAGE.format(file_md5), stage
        )
        await redis_client.set(
            RedisKey.FILE_VECTORIZATION_TASK_UPDATED_AT.format(file_md5),
            int(time.time()),
        )
        await self._touch_ttl(file_md5)

    async def get_cursor(self, file_md5: str) -> str | None:
        if self.redis is None:
            return None
        redis_client = cast(Any, self.redis)
        return await redis_client.get(
            RedisKey.FILE_VECTORIZATION_TASK_CURSOR.format(file_md5)
        )

    async def set_cursor(self, file_md5: str, cursor: str) -> None:
        if self.redis is None:
            return
        redis_client = cast(Any, self.redis)
        await redis_client.set(
            RedisKey.FILE_VECTORIZATION_TASK_CURSOR.format(file_md5), cursor
        )
        await self._touch_ttl(file_md5)

    async def clear(self, file_md5: str) -> None:
        """清理当前 file_md5 的向量化任务相关 key。"""
        if self.redis is None:
            return
        redis_client = cast(Any, self.redis)
        await redis_client.delete(
            RedisKey.FILE_VECTORIZATION_TASK_STATUS.format(file_md5),
            RedisKey.FILE_VECTORIZATION_TASK_ERROR.format(file_md5),
            RedisKey.FILE_VECTORIZATION_TASK_STAGE.format(file_md5),
            RedisKey.FILE_VECTORIZATION_TASK_ERROR_CODE.format(file_md5),
            RedisKey.FILE_VECTORIZATION_TASK_ERROR_MESSAGE.format(file_md5),
            RedisKey.FILE_VECTORIZATION_TASK_RETRYABLE.format(file_md5),
            RedisKey.FILE_VECTORIZATION_TASK_UPDATED_AT.format(file_md5),
            RedisKey.FILE_VECTORIZATION_TASK_CURSOR.format(file_md5),
        )

    async def _touch_ttl(self, file_md5: str) -> None:
        """刷新任务相关 key 的 TTL，防止永久残留。"""
        if self.redis is None:
            return
        ttl = get_settings().VECTOR_TASK_TTL_SECONDS
        redis_client = cast(Any, self.redis)
        await redis_client.expire(
            RedisKey.FILE_VECTORIZATION_TASK_STATUS.format(file_md5), ttl
        )
        await redis_client.expire(
            RedisKey.FILE_VECTORIZATION_TASK_ERROR.format(file_md5), ttl
        )
        await redis_client.expire(
            RedisKey.FILE_VECTORIZATION_TASK_STAGE.format(file_md5), ttl
        )
        await redis_client.expire(
            RedisKey.FILE_VECTORIZATION_TASK_ERROR_CODE.format(file_md5), ttl
        )
        await redis_client.expire(
            RedisKey.FILE_VECTORIZATION_TASK_ERROR_MESSAGE.format(file_md5), ttl
        )
        await redis_client.expire(
            RedisKey.FILE_VECTORIZATION_TASK_RETRYABLE.format(file_md5), ttl
        )
        await redis_client.expire(
            RedisKey.FILE_VECTORIZATION_TASK_UPDATED_AT.format(file_md5), ttl
        )
        await redis_client.expire(
            RedisKey.FILE_VECTORIZATION_TASK_CURSOR.format(file_md5), ttl
        )
