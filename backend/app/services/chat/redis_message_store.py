from __future__ import annotations

from typing import Callable

from app.models import ChatMessage
from app.services.memory.redis_memory import RedisChatMemory


class RedisMessageStore:
    def __init__(self, redis_memory_factory: Callable[[int], RedisChatMemory]) -> None:
        self.redis_memory_factory = redis_memory_factory

    async def append_message(self, session_id: int, message: ChatMessage) -> None:
        await self.redis_memory_factory(session_id).append_message(
            {
                "id": message.id,
                "session_id": message.session_id,
                "user_id": message.user_id,
                "role": message.role,
                "content": message.content,
                "model_name": message.model_name,
                "token_count": message.token_count,
                "create_time": message.create_time.isoformat()
                if message.create_time
                else "",
            }
        )
