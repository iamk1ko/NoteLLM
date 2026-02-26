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
        cache_hit = False

        # 只用用户当前 query 进行检索，不再拼接历史
        # 历史对话用于 LLM 生成上下文，不用于 RAG 检索
        query_text = query.text
        cache_key = self._cache_key(query_text, query.top_k, query.filters)

        if self.cache:
            cached = await self.cache.get(cache_key)
            if cached:
                cache_hit = True
                hits = [self._hit_from_dict(item) for item in cached["hits"]]
                elapsed_ms = int((time.time() - start) * 1000)
                logger.info(
                    "RAG检索(缓存命中): session_id={}, query={}, top_k={}, "
                    "elapsed_ms={}, hits={}",
                    query.session_id,
                    query_text[:50] + "..." if len(query_text) > 50 else query_text,
                    query.top_k,
                    elapsed_ms,
                    len(hits),
                )
                return RagResult(
                    query=query,
                    hits=hits,
                    elapsed_ms=elapsed_ms,
                )

        dense_hits, bm25_hits = await self.retriever.retrieve(
            query_text, query.top_k, query.filters
        )
        ranked = self.ranker.merge_and_rank(dense_hits, bm25_hits, query.top_k)

        if self.cache:
            await self.cache.set(cache_key, {"hits": [hit.__dict__ for hit in ranked]})

        elapsed_ms = int((time.time() - start) * 1000)
        logger.info(
            "RAG检索: session_id={}, query={}, top_k={}, elapsed_ms={}, "
            "dense_hits={}, bm25_hits={}, final_hits={}",
            query.session_id,
            query_text[:50] + "..." if len(query_text) > 50 else query_text,
            query.top_k,
            elapsed_ms,
            len(dense_hits),
            len(bm25_hits),
            len(ranked),
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
