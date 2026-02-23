from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RagQuery:
    text: str
    session_id: int | None = None
    top_k: int = 5
    filters: dict[str, Any] | None = None


@dataclass
class RagHit:
    chunk_id: str
    content: str
    score: float
    source: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RagResult:
    query: RagQuery
    hits: list[RagHit]
    elapsed_ms: int
