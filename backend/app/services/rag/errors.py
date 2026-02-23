from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RagStage(str, Enum):
    EMBED = "embed"
    DENSE_RETRIEVE = "dense_retrieve"
    BM25_RETRIEVE = "bm25_retrieve"
    MERGE = "merge"


@dataclass
class RagError(Exception):
    stage: RagStage
    message: str
    code: str = "rag_error"
    retryable: bool = True
    cause: Exception | None = None

    def __post_init__(self) -> None:
        super().__init__(self.message)

    def __str__(self) -> str:
        return self.message
