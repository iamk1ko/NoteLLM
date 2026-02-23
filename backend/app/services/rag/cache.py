from __future__ import annotations

import json
from typing import Any

from redis.asyncio import Redis


class RagCache:
    def __init__(self, redis_client: Redis | None, ttl_seconds: int = 300) -> None:
        self.redis = redis_client
        self.ttl_seconds = ttl_seconds

    async def get(self, key: str) -> dict[str, Any] | None:
        if self.redis is None:
            return None
        raw = await self.redis.get(key)
        if not raw:
            return None
        return json.loads(raw)

    async def set(self, key: str, value: dict[str, Any]) -> None:
        if self.redis is None:
            return
        await self.redis.set(key, json.dumps(value), ex=self.ttl_seconds)
