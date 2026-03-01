from __future__ import annotations

from typing import Protocol

from langchain_openai import OpenAIEmbeddings
from pydantic import SecretStr

from app.core.settings import get_settings


class Embedder(Protocol):
    @property
    def dim(self) -> int: ...

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]: ...

    async def aembed_queries(self, texts: list[str]) -> list[list[float]]: ...


class OpenAIEmbeddingAdapter:
    def __init__(
            self,
            *,
            model: str,
            api_key: str,
            base_url: str,
            dimensions: int,
    ) -> None:
        self._dimensions = dimensions
        self._client = OpenAIEmbeddings(
            model=model,
            api_key=SecretStr(api_key),
            base_url=base_url,
            dimensions=dimensions,
        )

    @property
    def dim(self) -> int:
        return self._dimensions

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        return await self._client.aembed_documents(texts=texts)

    async def aembed_queries(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = []
        for text in texts:
            vectors.append(await self._client.aembed_query(text=text))
        return vectors


def build_default_embedder() -> OpenAIEmbeddingAdapter:
    settings = get_settings()
    if not settings.BLSC_API_KEY or not settings.BLSC_BASE_URL:
        raise RuntimeError("LLM API 未配置，无法初始化 Embedding 客户端")

    return OpenAIEmbeddingAdapter(
        model=settings.EMBEDDING_MODEL_NAME,
        api_key=settings.BLSC_API_KEY,
        base_url=settings.BLSC_BASE_URL,
        dimensions=settings.EMBEDDING_DIM,
    )
