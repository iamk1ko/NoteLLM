from __future__ import annotations

from typing import Protocol

from pymilvus.model.hybrid.bge_m3 import BGEM3EmbeddingFunction


class Embedder(Protocol):
    @property
    def dim(self) -> int: ...

    def encode_documents(self, texts: list[str]) -> dict: ...

    def encode_queries(self, texts: list[str]) -> dict: ...


class BgeM3Embedder:
    def __init__(
        self,
        *,
        model_name: str,
        device: str,
        use_fp16: bool,
        model_path: str | None = None,
    ) -> None:
        resolved_name = model_path or model_name
        self._model = BGEM3EmbeddingFunction(
            model_name=resolved_name,
            device=device,
            use_fp16=use_fp16,
        )

    @property
    def dim(self) -> int:
        return self._model.dim["dense"]

    def encode_documents(self, texts: list[str]) -> dict:
        return self._model.encode_documents(texts)

    def encode_queries(self, texts: list[str]) -> dict:
        return self._model.encode_queries(texts)
