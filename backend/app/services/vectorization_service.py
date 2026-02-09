from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
import tempfile
from typing import Any, Iterable, cast

from minio import Minio
from pypdf import PdfReader  # type: ignore[import-not-found]
from redis.asyncio import Redis
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.redis_client import FILE_VECTORIZATION_KEY
from app.crud.file_storage_crud import FileStorageCRUD
from app.crud.rag_chunks_crud import RagChunksCRUD
from app.models.file_storage import FileStorageStatus

logger = get_logger(__name__)


@dataclass
class RagChunkPayload:
    chunk_index: int
    chunk_text: str
    chunk_tokens: int
    page_no: int | None = None
    section: str | None = None


class SimpleVectorStoreClient:
    """简化版向量库客户端占位实现。"""

    def upsert_texts(
            self, texts: list[str], metadatas: list[dict[str, Any]]
    ) -> list[str]:
        """将文本向量化并存储，返回对应的embedding_id列表。

        说明:
            upsert 是由 update 和 insert 合成的术语。含义是：先尝试根据主键或唯一键更新已存在的记录，若不存在则插入一条新记录。
            表示为给定文本创建或更新向量/embedding：若对应的 embedding 已存在则覆盖/更新，否则新增并返回对应的 id。
        """
        embedding_ids: list[str] = []
        for text in texts:
            embedding_ids.append(hashlib.md5(text.encode("utf-8")).hexdigest())
        return embedding_ids


class VectorizationService:
    def __init__(
            self,
            db: Session,
            redis_client: Redis | None = None,
            minio_client: Minio | None = None,
            vector_store: SimpleVectorStoreClient | None = None,
    ):
        self.db = db
        self.redis = redis_client
        self.minio = minio_client
        self.vector_store = vector_store or SimpleVectorStoreClient()

    async def vectorize_file(
            self,
            *,
            file_id: int,
            file_md5: str,
            bucket_name: str,
            object_name: str,
            content_type: str,
    ) -> int:
        if self.minio is None:
            raise RuntimeError("MinIO 客户端连接失败了...")

        await self._set_task_status(file_md5, "running")
        chunk_total = 0

        temp_path = self._download_object_to_tempfile(bucket_name, object_name)
        try:
            for chunk in self._iter_chunks_from_file(temp_path, content_type):
                embedding_ids = self.vector_store.upsert_texts(
                    [chunk.chunk_text],
                    [
                        {
                            "file_id": file_id,
                            "chunk_index": chunk.chunk_index,
                            "page_no": chunk.page_no,
                            "section": chunk.section,
                        }
                    ],
                )
                RagChunksCRUD.create_chunks(
                    self.db,
                    file_id=file_id,
                    chunks=[chunk],
                    embedding_ids=embedding_ids,
                )
                chunk_total += 1
            FileStorageCRUD.update_file_status(
                self.db, file_id=file_id, status=FileStorageStatus.EMBEDDED.value
            )
            await self._set_task_status(file_md5, "success")
            return chunk_total
        except Exception:
            await self._set_task_status(file_md5, "failed")
            raise
        finally:
            try:
                os.remove(temp_path)
            except Exception:
                logger.warning("无法删除临时文件：{}", temp_path)

    def _download_object_to_tempfile(self, bucket_name: str, object_name: str) -> str:
        minio_client = cast(Any, self.minio)
        obj = minio_client.get_object(bucket_name, object_name)
        try:
            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                for data in obj.stream(32 * 1024):  # 32KB块读取
                    tmp_file.write(data)
                return tmp_file.name
        finally:
            obj.close()
            obj.release_conn()

    def _iter_chunks_from_file(
            self, file_path: str, content_type: str
    ) -> Iterable[RagChunkPayload]:
        chunk_size = 768
        overlap = 120

        if content_type == "application/pdf" or file_path.lower().endswith(".pdf"):
            reader = PdfReader(file_path)
            chunk_index = 0
            for page_no, page in enumerate(reader.pages, start=1):
                text = page.extract_text() or ""
                if not text.strip():
                    continue
                page_chunks = list(
                    self._chunk_text(text, chunk_index, chunk_size, overlap)
                )
                for chunk in page_chunks:
                    chunk.page_no = page_no
                    yield chunk
                chunk_index += len(page_chunks)
            return

        with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
            text = file.read()
        for chunk in self._chunk_text(text, 0, chunk_size, overlap):
            yield chunk

    def _chunk_text(
            self, text: str, start_index: int, chunk_size: int, overlap: int
    ) -> Iterable[RagChunkPayload]:
        words = text.split()
        if not words:
            return

        if overlap >= chunk_size:
            overlap = max(0, chunk_size // 4)

        index = start_index
        start = 0
        while start < len(words):
            end = min(start + chunk_size, len(words))
            chunk_words = words[start:end]
            chunk_text = " ".join(chunk_words)
            yield RagChunkPayload(
                chunk_index=index,
                chunk_text=chunk_text,
                chunk_tokens=len(chunk_words),
            )
            index += 1
            if end == len(words):
                break
            start = max(0, end - overlap)

    async def _set_task_status(self, file_md5: str, status: str) -> None:
        if self.redis is None:
            return
        redis_client = cast(Any, self.redis)
        await redis_client.set(FILE_VECTORIZATION_KEY.format(file_md5), status)
