from __future__ import annotations

from typing import Iterable

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.rag_chunks import RagChunks

logger = get_logger(__name__)


class RagChunksCRUD:
    """语义切片与向量表操作。"""

    @staticmethod
    def create_chunks(
        db: Session,
        *,
        file_id: int,
        chunks: Iterable[object],
        embedding_ids: list[str],
    ) -> None:
        records: list[RagChunks] = []
        for idx, chunk in enumerate(chunks):
            embedding_id = embedding_ids[idx] if idx < len(embedding_ids) else None
            record = RagChunks(
                file_id=file_id,
                chunk_index=getattr(chunk, "chunk_index"),
                chunk_text=getattr(chunk, "chunk_text"),
                chunk_tokens=getattr(chunk, "chunk_tokens"),
                page_no=getattr(chunk, "page_no", None),
                section=getattr(chunk, "section", None),
                embedding_id=embedding_id,
                status=1,
            )
            records.append(record)

        if not records:
            return

        db.add_all(records)
        db.commit()
        logger.debug(
            "新增 rag_chunks 记录：file_id={}, count={}", file_id, len(records)
        )
