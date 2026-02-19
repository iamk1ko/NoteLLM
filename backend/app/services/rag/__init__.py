from __future__ import annotations

"""RAG service package.

Keep this module light: importing `app.services.rag` (or any submodule like
`app.services.rag.cache`) shouldn't eagerly import Milvus/vectorization or other
heavy dependencies. We expose convenience symbols via lazy imports.
"""

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from app.services.rag.bm25_retriever import Bm25Retriever
    from app.services.rag.cache import RagCache
    from app.services.rag.dense_retriever import DenseRetriever
    from app.services.rag.errors import RagError, RagStage
    from app.services.rag.memory import ConversationMemory
    from app.services.rag.orchestrator import RagOrchestrator
    from app.services.rag.ranker import HybridRanker
    from app.services.rag.retriever import HybridRetriever
    from app.services.rag.schemas import RagHit, RagQuery, RagResult

__all__ = [
    "Bm25Retriever",
    "RagCache",
    "DenseRetriever",
    "RagError",
    "RagStage",
    "ConversationMemory",
    "RagOrchestrator",
    "HybridRanker",
    "HybridRetriever",
    "RagHit",
    "RagQuery",
    "RagResult",
]


def __getattr__(name: str) -> Any:  # PEP 562
    if name == "RagCache":
        from app.services.rag.cache import RagCache as _RagCache

        return _RagCache
    if name == "Bm25Retriever":
        from app.services.rag.bm25_retriever import Bm25Retriever as _Bm25Retriever

        return _Bm25Retriever
    if name == "DenseRetriever":
        from app.services.rag.dense_retriever import DenseRetriever as _DenseRetriever

        return _DenseRetriever
    if name in {"RagError", "RagStage"}:
        from app.services.rag.errors import RagError as _RagError, RagStage as _RagStage

        return _RagError if name == "RagError" else _RagStage
    if name == "ConversationMemory":
        from app.services.rag.memory import ConversationMemory as _ConversationMemory

        return _ConversationMemory
    if name == "RagOrchestrator":
        from app.services.rag.orchestrator import RagOrchestrator as _RagOrchestrator

        return _RagOrchestrator
    if name == "HybridRanker":
        from app.services.rag.ranker import HybridRanker as _HybridRanker

        return _HybridRanker
    if name == "HybridRetriever":
        from app.services.rag.retriever import HybridRetriever as _HybridRetriever

        return _HybridRetriever
    if name in {"RagHit", "RagQuery", "RagResult"}:
        from app.services.rag.schemas import RagHit as _RagHit, RagQuery as _RagQuery, RagResult as _RagResult

        return {"RagHit": _RagHit, "RagQuery": _RagQuery, "RagResult": _RagResult}[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
