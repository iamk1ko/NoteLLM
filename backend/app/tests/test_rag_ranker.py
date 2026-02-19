from __future__ import annotations

from app.services.rag.ranker import HybridRanker


def test_ranker_merges_and_sorts():
    ranker = HybridRanker(alpha=0.5)
    dense = [
        {"id": "1", "score": 0.9, "text": "dense-1", "metadata": {"chunk_index": 1}},
        {"id": "2", "score": 0.5, "text": "dense-2", "metadata": {"chunk_index": 2}},
    ]
    bm25 = [
        {"id": "1", "score": 0.2, "text": "dense-1", "metadata": {"chunk_index": 1}},
        {"id": "3", "score": 0.8, "text": "bm25-3", "metadata": {"chunk_index": 3}},
    ]

    results = ranker.merge_and_rank(dense, bm25, top_k=2)

    assert len(results) == 2
    assert results[0].chunk_id in {"1", "3"}
    assert results[0].score >= results[1].score
