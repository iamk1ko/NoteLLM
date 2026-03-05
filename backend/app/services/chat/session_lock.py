from __future__ import annotations

from typing import Callable

from app.core.constants import RedisKey
from app.core.logging import get_logger
from app.core.settings import get_settings
from app.services.memory.redis_memory import RedisChatMemory

logger = get_logger(__name__)


class RedisSessionLock:
    def __init__(
        self, redis_memory_factory: Callable[[int], RedisChatMemory], session_id: int
    ) -> None:
        self.redis_memory_factory = redis_memory_factory
        self.session_id = session_id
        self.lock_key = RedisKey.CHAT_SESSION_CACHE_FLAG.format(session_id) + ":lock"
        self.acquired = False

    async def acquire(self) -> bool:
        try:
            redis_client = self.redis_memory_factory(self.session_id).redis
            settings = get_settings()
            self.acquired = await redis_client.set(
                self.lock_key,
                "1",
                ex=settings.REDIS_SESSION_LOCK_TTL_SECONDS,
                nx=True,
            )
            if not self.acquired:
                logger.warning(
                    "会话锁占用中，继续流式响应: session_id={}", self.session_id
                )
        except Exception:
            self.acquired = False
        return self.acquired

    async def release(self) -> None:
        if not self.acquired:
            return
        try:
            redis_client = self.redis_memory_factory(self.session_id).redis
            await redis_client.delete(self.lock_key)
        except Exception:
            logger.warning("释放会话锁失败: session_id={}", self.session_id)
