from __future__ import annotations

from app.core.constants import MilvusField
from app.core.logging import get_logger
from app.core.settings import get_settings
from app.services.vectorization.vector_store import MilvusVectorStore

logger = get_logger(__name__)


class RagSearchService:
    def __init__(self, milvus: MilvusVectorStore | None) -> None:
        self.milvus = milvus

    async def search(self, query: str, file_id: str | None) -> str:
        if not file_id or not self.milvus:
            return ""

        try:
            settings = get_settings()
            filters = (
                {MilvusField.FILE_ID.value: int(file_id)} if file_id.isdigit() else None
            )

            results = await self.milvus.search_hybrid(
                query=query,
                k=settings.RAG_TOP_K,
                filters=filters,
            )
            logger.info(
                "RAG 混合检索完成: query='{}', top_k={}, raw_results={}",
                query,
                settings.RAG_TOP_K,
                results,
            )

            if results:
                context = "\n\n".join(
                    [
                        f"【来源 {i + 1}】{r.get('text', r.get('content', ''))}"
                        for i, r in enumerate(results)
                    ]
                )
                logger.info("RAG 检索到 {} 条结果", len(results))
                return context

        except Exception as e:
            logger.warning("RAG 检索失败: {}", e)

        return ""
