from __future__ import annotations

import json
from datetime import datetime

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
        self._key = RedisKey.CHAT_SESSION_MESSAGES.format(session_id)
        self._cache_flag_key = RedisKey.CHAT_SESSION_CACHE_FLAG.format(session_id)

    async def get_recent_messages(self, limit: int | None = None) -> list[dict]:
        """获取最近的 N 条消息（从 Redis）"""
        count = limit or self.memory_limit

        # 从 Redis 获取最近的消息
        messages = await self.redis.lrange(self._key, 0, count - 1)

        if not messages:
            return []

        return [json.loads(msg) for msg in messages]

    async def append_message(self, role: str, content: str) -> None:
        """追加消息到记忆（左侧入队，实现滑动窗口）"""
        message = {
            "role": role,
            "content": content,
            "create_time": datetime.now().isoformat(),
        }

        # 左侧入队
        await self.redis.lpush(self._key, json.dumps(message, ensure_ascii=False))

        # 维护滑动窗口大小
        await self.redis.ltrim(self._key, 0, self.memory_limit - 1)

        # 设置缓存标记
        await self.redis.set(self._cache_flag_key, "1", ex=86400)  # 24小时过期

        logger.debug("Redis 追加消息: session_id={}, role={}", self.session_id, role)

    async def load_from_mysql(self, db: AsyncSession) -> None:
        """从 MySQL 加载完整历史到 Redis（仅首次加载）"""
        # 检查是否已加载
        cached = await self.redis.get(self._cache_flag_key)
        if cached:
            logger.debug("Redis 缓存已存在，跳过加载: session_id={}", self.session_id)
            return

        # 从 MySQL 加载
        messages = await ChatMessageCRUD.get_recent_messages_async(
            db, session_id=self.session_id, limit=self.memory_limit
        )

        # 按时间正序存储（最早的在前）
        # Redis lpush 是最新的在前，所以我们需要反转
        messages_list = [
            {
                "role": msg.role,
                "content": msg.content,
                "create_time": msg.create_time.isoformat() if msg.create_time else "",
            }
            for msg in reversed(messages)
        ]

        if messages_list:
            # 批量写入 Redis
            pipe = self.redis.pipeline()
            for msg in messages_list:
                await pipe.lpush(
                    self._key, json.dumps(msg, ensure_ascii=False)
                )  # 左侧入队
            await pipe.ltrim(
                self._key, 0, self.memory_limit - 1
            )  # 维护滑动窗口大小, 删除多余的历史消息
            await pipe.set(
                self._cache_flag_key, "1", ex=86400
            )  # 设置缓存标记，24小时过期
            await pipe.execute()  # 执行批量操作

        logger.info(
            "从 MySQL 加载历史到 Redis: session_id={}, count={}",
            self.session_id,
            len(messages_list),
        )

    async def get_context_for_llm(self, limit: int | None = None) -> list[dict]:
        """获取用于 LLM 上下文的对话历史"""
        messages = await self.get_recent_messages(limit)

        # 转换为 LLM 需要的格式
        return [{"role": msg["role"], "content": msg["content"]} for msg in messages]

    async def clear(self) -> None:
        """清除会话的 Redis 缓存"""
        await self.redis.delete(self._key, self._cache_flag_key)
        logger.info("清除 Redis 记忆: session_id={}", self.session_id)
