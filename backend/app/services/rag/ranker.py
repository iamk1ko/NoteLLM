from __future__ import annotations

from typing import Any

from app.services.rag.schemas import RagHit


class HybridRanker:
    def __init__(self, alpha: float = 0.7) -> None:
        self.alpha = alpha

    def merge_and_rank(
            self,
            dense_hits: list[dict],
            bm25_hits: list[dict],
            top_k: int,
    ) -> list[RagHit]:
        scored: dict[str, dict[str, Any]] = {}

        def update(_hit: dict, source: str, score: float) -> None:
            _chunk_id = self._chunk_id(_hit)
            if _chunk_id not in scored:
                scored[_chunk_id] = {
                    "hit": _hit,
                    "dense": 0.0,
                    "bm25": 0.0,
                    "source": set(),
                }
            scored[_chunk_id]["source"].add(source)
            if source == "dense":
                scored[_chunk_id]["dense"] = max(scored[_chunk_id]["dense"], score)
            else:
                scored[_chunk_id]["bm25"] = max(scored[_chunk_id]["bm25"], score)

        for hit in dense_hits:
            update(hit, "dense", float(hit.get("score", 0.0)))
        for hit in bm25_hits:
            update(hit, "bm25", float(hit.get("score", 0.0)))

        merged: list[RagHit] = []
        for chunk_id, entry in scored.items():
            dense_score = entry["dense"]
            bm25_score = entry["bm25"]
            score = self.alpha * dense_score + (1.0 - self.alpha) * bm25_score
            hit = entry["hit"]
            merged.append(
                RagHit(
                    chunk_id=chunk_id,
                    content=self._content(hit),
                    score=score,
                    source="+".join(sorted(entry["source"])),
                    metadata=hit.get("metadata", {}),
                )
            )

        merged.sort(key=lambda item: item.score, reverse=True)
        return merged[:top_k]

    @staticmethod
    def _chunk_id(hit: dict) -> str:
        meta = hit.get("metadata", {})
        file_id = meta.get("file_id")
        chunk_index = meta.get("chunk_index")
        if file_id is not None and chunk_index is not None:
            return f"{file_id}:{chunk_index}"
        return str(hit.get("id", "unknown"))

    @staticmethod
    def _content(hit: dict) -> str:
        return hit.get("text") or hit.get("content") or ""
