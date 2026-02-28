from __future__ import annotations

import json

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import RedisKey
from app.core.logging import get_logger
from app.core.settings import get_settings
from app.crud.chat_message_crud import ChatMessageCRUD

logger = get_logger(__name__)


class RedisChatMemory:
    """Redis 短期记忆服务 - 滑动窗口式存储"""

    def __init__(
            self,
            redis_client: Redis,
            session_id: int,
            memory_limit: int | None = None,
    ) -> None:
        settings = get_settings()
        self.redis = redis_client
        self.session_id = session_id
        self.memory_limit = memory_limit or settings.REDIS_MEMORY_LIMIT
        self.ttl_seconds = settings.REDIS_CHAT_TTL_SECONDS
        self._key = RedisKey.CHAT_SESSION_MESSAGES.format(session_id)
        self._cache_flag_key = RedisKey.CHAT_SESSION_CACHE_FLAG.format(session_id)

    async def _refresh_ttl(self) -> None:
        await self.redis.expire(self._key, self.ttl_seconds)
        await self.redis.expire(self._cache_flag_key, self.ttl_seconds)

    async def has_cache(self) -> bool:
        cached = await self.redis.get(self._cache_flag_key)
        return bool(cached)

    async def get_recent_messages(self, limit: int | None = None) -> list[dict]:
        """获取最近的 N 条消息（从 Redis）"""
        count = limit or self.memory_limit

        if count <= 0:
            return []

        # 从 Redis 获取最近的消息（按时间正序）
        messages = await self.redis.lrange(self._key, -count, -1)

        if not messages:
            return []

        await self._refresh_ttl()
        return [json.loads(msg) for msg in messages]

    async def append_message(self, message: dict) -> None:
        """追加消息到记忆（按时间正序，右侧入队）"""
        await self.redis.rpush(self._key, json.dumps(message, ensure_ascii=False))
        await self.redis.set(self._cache_flag_key, "1", ex=self.ttl_seconds)
        await self._refresh_ttl()

        logger.debug(
            "Redis 追加消息: session_id={}, role={}, msg_id={}",
            self.session_id,
            message.get("role"),
            message.get("id"),
        )

    async def load_from_mysql(self, db: AsyncSession) -> None:
        """从 MySQL 加载完整历史到 Redis（仅首次加载）"""
        if await self.has_cache():
            logger.debug("Redis 缓存已存在，跳过加载: session_id={}", self.session_id)
            await self._refresh_ttl()
            return

        page = 1
        size = 200
        total_loaded = 0

        pipe = self.redis.pipeline()
        while True:
            messages, total = await ChatMessageCRUD.get_session_messages_async(
                db, session_id=self.session_id, page=page, size=size
            )
            if not messages:
                break

            for msg in messages:
                payload = {
                    "id": msg.id,
                    "session_id": msg.session_id,
                    "user_id": msg.user_id,
                    "role": msg.role,
                    "content": msg.content,
                    "model_name": msg.model_name,
                    "token_count": msg.token_count,
                    "create_time": msg.create_time.isoformat()
                    if msg.create_time
                    else "",
                }
                await pipe.rpush(self._key, json.dumps(payload, ensure_ascii=False))
                total_loaded += 1

            if total_loaded >= total:
                break
            page += 1

        await pipe.set(self._cache_flag_key, "1", ex=self.ttl_seconds)
        await pipe.execute()
        await self._refresh_ttl()

        logger.info(
            "从 MySQL 加载历史到 Redis: session_id={}, count={}, expires_ttl={}s",
            self.session_id,
            total_loaded,
            self.ttl_seconds,
        )

    async def get_messages_page(self, page: int, size: int) -> tuple[list[dict], int]:
        """分页获取消息（从 Redis），返回消息列表和总数"""
        if page < 1 or size < 1:
            return [], 0
        start = (page - 1) * size
        end = start + size - 1

        total = await self.redis.llen(self._key)
        if total == 0:
            return [], 0

        messages = await self.redis.lrange(self._key, start, end)
        await self._refresh_ttl()
        return [json.loads(msg) for msg in messages], int(total)

    async def get_context_for_llm(self) -> list[dict]:
        """获取用于 LLM 上下文的对话历史"""
        messages = await self.get_recent_messages(self.memory_limit)

        logger.debug(
            "从 Redis 中加载用于 LLM 上下文的消息: session_id={}, count={}",
            self.session_id,
            len(messages),
        )

        # 转换为 LLM 需要的格式
        return [{"role": msg["role"], "content": msg["content"]} for msg in messages]

    async def clear(self) -> None:
        """清除会话的 Redis 缓存"""
        await self.redis.delete(self._key, self._cache_flag_key)
        logger.info("清除 Redis 记忆: session_id={}", self.session_id)
