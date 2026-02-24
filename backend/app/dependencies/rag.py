from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.core.db import get_async_db
from app.dependencies.infra import get_redis, get_milvus
from app.services.rag.service import RagService
from app.services.vectorization.embedder import BgeM3Embedder
from app.core.settings import get_settings


async def get_rag_service(
    db: AsyncSession = Depends(get_async_db),
    redis_client: Redis = Depends(get_redis),
    milvus: MilvusVectorStore = Depends(get_milvus),
) -> RagService:
    """获取 RAG 服务实例（异步）。"""

    settings = get_settings()

    embedder = BgeM3Embedder(
        model_name=settings.EMBEDDING_MODEL_NAME,
        device=settings.EMBEDDING_DEVICE,
        use_fp16=False,
    )

    return RagService(
        db=db,
        redis_client=redis_client,
        vector_store=milvus,
        embedder=embedder,
        history_limit=settings.RAG_HISTORY_LIMIT,
        cache_ttl_seconds=settings.RAG_CACHE_TTL,
        alpha=settings.RAG_RANKER_ALPHA,
    )
