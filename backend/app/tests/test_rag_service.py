from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, AsyncMock
import pytest

from app.services.rag.service import RagService
from app.services.rag.schemas import RagQuery


class _MockVectorStore:
    async def search_dense(self, query_vector, k, filters):
        return [
            {
                "id": "1",
                "chunk_id": "1",
                "score": 0.9,
                "content": "dense_hit",
                "metadata": {"chunk_index": 1},
                "source": "s1",
            }
        ]

    async def search_bm25(self, query, k, filters):
        return [
            {
                "id": "2",
                "chunk_id": "2",
                "score": 0.3,
                "content": "bm25_hit",
                "metadata": {"chunk_index": 2},
                "source": "s2",
            }
        ]


class _MockEmbedder:
    @property
    def dim(self):
        return 768

    async def aencode_queries(self, texts):
        return [[0.1] * 768]

    async def aencode_documents(self, texts):
        return [[0.1] * 768]


@pytest.mark.asyncio
async def test_rag_service_search():
    # Setup Mocks
    mock_db = MagicMock()
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None  # Cache miss

    mock_vector_store = _MockVectorStore()
    mock_embedder = _MockEmbedder()

    # Instantiate Service
    service = RagService(
        db=mock_db,
        redis_client=mock_redis,
        vector_store=mock_vector_store,
        embedder=mock_embedder,
        history_limit=2,
    )

    # Mock Memory
    service.memory.get_recent_messages = AsyncMock(return_value=["history"])

    # Execute Search
    query = RagQuery(text="test query", session_id=1, top_k=2)
    result = await service.search(query)

    # Assertions
    assert len(result.hits) == 2
    assert (
        result.hits[0].content == "dense_hit" or result.hits[1].content == "dense_hit"
    )
    assert result.hits[0].content == "bm25_hit" or result.hits[1].content == "bm25_hit"
