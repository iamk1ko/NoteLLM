from __future__ import annotations

import asyncio

from app.services.rag.cache import RagCache


class _FakeRedis:
    def __init__(self):
        self.data = {}

    async def get(self, key):
        return self.data.get(key)

    async def set(self, key, value, ex=None):
        self.data[key] = value


def test_cache_roundtrip():
    cache = RagCache(_FakeRedis(), ttl_seconds=1)
    asyncio.run(cache.set("k", {"hits": ["a"]}))
    value = asyncio.run(cache.get("k"))
    assert value == {"hits": ["a"]}
