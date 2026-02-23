from __future__ import annotations

import hashlib
import time

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.services.rag.cache import RagCache
from app.services.rag.memory import ConversationMemory
from app.services.rag.ranker import HybridRanker
from app.services.rag.retriever import HybridRetriever
from app.services.rag.schemas import RagQuery, RagResult, RagHit
from app.services.vectorization.embedder import Embedder
from app.services.vectorization.vector_store import MilvusVectorStore

logger = get_logger(__name__)


class RagService:
    def __init__(
            self,
            *,
            db: Session | AsyncSession,
            redis_client: Redis | None,
            vector_store: MilvusVectorStore,
            embedder: Embedder,
            history_limit: int = 8,
            cache_ttl_seconds: int = 300,
            alpha: float = 0.7,
    ) -> None:
        self.memory = ConversationMemory(db, history_limit=history_limit)
        self.retriever = HybridRetriever(
            embedder=embedder,
            vector_store=vector_store,
        )
        self.ranker = HybridRanker(alpha=alpha)
        self.cache = RagCache(redis_client, ttl_seconds=cache_ttl_seconds)

    async def search(self, query: RagQuery) -> RagResult:
        start = time.time()
        # TODO: 这里将用户query与对话历史拼接后进行检索，可能会导致缓存失效。后续可以考虑只用用户query做检索，或者对拼接后的文本做hash来生成缓存key。
        query_text = await self._with_context(query)
        cache_key = self._cache_key(query_text, query.top_k, query.filters)

        if self.cache:
            cached = await self.cache.get(cache_key)
            if cached:
                hits = [self._hit_from_dict(item) for item in cached["hits"]]
                return RagResult(
                    query=query,
                    hits=hits,
                    elapsed_ms=int((time.time() - start) * 1000),
                )

        dense_hits, bm25_hits = await self.retriever.retrieve(
            query_text, query.top_k, query.filters
        )
        ranked = self.ranker.merge_and_rank(dense_hits, bm25_hits, query.top_k)

        if self.cache:
            await self.cache.set(cache_key, {"hits": [hit.__dict__ for hit in ranked]})

        elapsed_ms = int((time.time() - start) * 1000)
        logger.info(
            "RAG检索完成: session_id={}, top_k={}, elapsed_ms={}",
            query.session_id,
            query.top_k,
            elapsed_ms,
        )
        return RagResult(query=query, hits=ranked, elapsed_ms=elapsed_ms)

    async def _with_context(self, query: RagQuery) -> str:
        history = await self.memory.get_recent_messages(query.session_id)
        if not history:
            return query.text
        return "\n".join(list(history) + [query.text])

    @staticmethod
    def _hit_from_dict(data: dict) -> RagHit:
        return RagHit(
            chunk_id=data.get("chunk_id", ""),
            content=data.get("content", ""),
            score=float(data.get("score", 0.0)),
            source=data.get("source", ""),
            metadata=data.get("metadata", {}),
        )

    @staticmethod
    def _cache_key(query: str, top_k: int, filters: dict | None) -> str:
        raw = f"{query}|{top_k}|{filters}"
        return "rag:" + hashlib.md5(raw.encode("utf-8")).hexdigest()
