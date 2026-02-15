from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class VectorizationStage(str, Enum):
    DOWNLOAD = "download"
    PARSE = "parse"
    CHUNK = "chunk"
    EMBED = "embed"
    STORE = "store"


@dataclass
class VectorizationError(Exception):
    stage: VectorizationStage
    message: str
    code: str = "vectorization_error"
    retryable: bool = True
    cause: Exception | None = None

    def __str__(self) -> str:
        return self.message

    def __post_init__(self) -> None:
        super().__init__(self.message)
