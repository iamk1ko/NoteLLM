from __future__ import annotations

from app.core.logging import get_logger
from app.services.rag.errors import RagError, RagStage
from app.services.vectorization.embedder import Embedder
from app.services.vectorization.vector_store import MilvusVectorStore

logger = get_logger(__name__)


class HybridRetriever:
    def __init__(
        self,
        *,
        embedder: Embedder,
        vector_store: MilvusVectorStore,
    ) -> None:
        self.embedder = embedder
        self.vector_store = vector_store

    async def retrieve(
        self, query: str, top_k: int, filters: dict | None = None
    ) -> tuple[list[dict], list[dict]]:
        dense_hits: list[dict] = []
        bm25_hits: list[dict] = []

        # Dense Retrieval
        try:
            # We encode the query into a dense vector
            # The Embedder protocol returns a dict like {"dense": [...], "sparse": ...}
            # We assume "dense" key holds the vector list
            encoding = self.embedder.encode_queries([query])
            # Depending on Embedder implementation, it might return a list of vectors or a dict
            # Based on previous file content: query_vector = self.embedder.encode_queries([query])["dense"][0]
            query_vector = encoding["dense"][0]

            dense_hits = await self.vector_store.search_dense(
                query_vector=query_vector, k=top_k, filters=filters
            )
        except Exception as e:
            logger.warning("语义检索失败，降级为 BM25：{}", e)
            # We don't raise here to allow partial results (BM25 only)

        # BM25 Retrieval
        try:
            bm25_hits = await self.vector_store.search_bm25(
                query=query, k=top_k, filters=filters
            )
        except Exception as e:
            # If BM25 also fails (or is the only one left), we might want to raise
            # But the original code raised RagError on BM25 failure.
            raise RagError(
                stage=RagStage.BM25_RETRIEVE,
                message="BM25 检索失败",
                code="bm25_failed",
                retryable=True,
                cause=e,
            ) from e

        if not dense_hits and not bm25_hits:
            logger.warning("检索无结果")

        return dense_hits, bm25_hits
