from __future__ import annotations

import asyncio

from app.services.rag.memory import ConversationMemory
from app.services.rag.orchestrator import RagOrchestrator
from app.services.rag.ranker import HybridRanker
from app.services.rag.retriever import HybridRetriever
from app.services.rag.schemas import RagQuery


class _Memory(ConversationMemory):
    def __init__(self):
        pass

    def get_recent_messages(self, session_id):
        return ["hello"]


class _Retriever(HybridRetriever):
    def __init__(self):
        pass

    async def retrieve(self, query: str, top_k: int, filters: dict | None = None):
        return (
            [{"id": "1", "score": 0.9, "text": "a", "metadata": {"chunk_index": 1}}],
            [{"id": "2", "score": 0.3, "text": "b", "metadata": {"chunk_index": 2}}],
        )


def test_orchestrator_basic():
    orchestrator = RagOrchestrator(
        memory=_Memory(),
        retriever=_Retriever(),
        ranker=HybridRanker(alpha=0.7),
        cache=None,
    )
    result = asyncio.run(
        orchestrator.search(RagQuery(text="question", session_id=1, top_k=2))
    )
    assert len(result.hits) == 2
