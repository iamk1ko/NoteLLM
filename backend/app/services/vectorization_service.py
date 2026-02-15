from __future__ import annotations

import json

from minio import Minio
from redis.asyncio import Redis
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.crud.file_storage_crud import FileStorageCRUD
from app.crud.rag_chunks_crud import RagChunksCRUD
from app.models.file_storage import FileStorageStatus
from app.services.vectorization import (
    DocumentParser,
    MinioFileReader,
    TaskStateStore,
    TextChunker,
    MilvusVectorStore,
)
from app.services.vectorization.vector_store import ChunkRecord

logger = get_logger(__name__)


class VectorizationService:
    def __init__(
            self,
            db: Session,
            redis_client: Redis | None = None,
            minio_client: Minio | None = None,
            *,
            memory_threshold_mb: int = 32,
            chunk_size: int = 768,
            overlap: int = 120,
            vector_batch_size: int = 64,
            vector_store: MilvusVectorStore | None = None,
    ):
        self.db = db
        self.redis = redis_client
        self.minio = minio_client
        if minio_client is None:
            raise RuntimeError("MinIO client is required for vectorization")
        self.reader = MinioFileReader(minio_client, memory_threshold_mb)
        self.parser = DocumentParser()
        self.chunker = TextChunker(chunk_size=chunk_size, overlap=overlap)
        self.task_state = TaskStateStore(redis_client)
        self.vector_store = vector_store
        self.vector_batch_size = vector_batch_size

    async def vectorize_file(
            self,
            *,  # * 表示以下参数必须以关键字参数形式传入，不能使用位置参数
            file_id: int,
            file_md5: str,
            bucket_name: str,
            object_name: str,
            content_type: str,
    ) -> int:
        # 幂等性检查：如果任务已成功完成，则直接返回
        existing_status = await self.task_state.get_status(file_md5)
        if existing_status == "success":
            logger.info("向量化任务已完成，跳过：file_md5={}", file_md5)
            return 0

        # 设置任务状态为 running，表示正在处理该文件的向量化任务
        await self.task_state.set_status(file_md5, "running")
        cursor_raw = await self.task_state.get_cursor(file_md5)
        last_chunk_index = -1
        if cursor_raw:
            try:
                cursor = json.loads(cursor_raw)
                last_chunk_index = int(cursor.get("chunk_index", -1))
            except (ValueError, TypeError, json.JSONDecodeError):
                last_chunk_index = -1
        chunk_total = 0

        # TODO: 这里的流程还有优化空间。比如可以边下载边解析边切片，减少等待时间。目前的实现是先下载完整文件到本地，再进行解析和切片。
        read_result = self.reader.download(bucket_name, object_name)
        try:
            elements = self.parser.parse(read_result.file_path, content_type)
            records: list[ChunkRecord] = []
            chunk_texts: list[str] = []

            for chunk in self.chunker.chunk_elements(elements):
                if chunk.chunk_index <= last_chunk_index:
                    continue
                chunk_texts.append(chunk.chunk_text)
                records.append(
                    ChunkRecord(
                        file_id=file_id,
                        file_md5=file_md5,
                        chunk_index=chunk.chunk_index,
                        page_no=chunk.page_no,
                        section=chunk.section,
                        content=chunk.chunk_text,
                        # sparse_vector=[], # 向量在后续批处理中会自动生成并更新
                        # dense_vector=[],
                        # metadata={},
                    )
                )

                if len(chunk_texts) >= self.vector_batch_size:
                    chunk_total += self._flush_batch(records)
                    await self.task_state.set_cursor(
                        file_md5,
                        json.dumps(
                            {
                                "chunk_index": records[-1].chunk_index,
                                "page_no": records[-1].page_no,
                            }
                        ),
                    )
                    records = []
                    chunk_texts = []

            if chunk_texts:
                chunk_total += self._flush_batch(records)
                await self.task_state.set_cursor(
                    file_md5,
                    json.dumps(
                        {
                            "chunk_index": records[-1].chunk_index,
                            "page_no": records[-1].page_no,
                        }
                    ),
                )

            FileStorageCRUD.update_file_status(
                self.db, file_id=file_id, status=FileStorageStatus.EMBEDDED.value
            )
            await self.task_state.set_status(file_md5, "success")
            return chunk_total
        except Exception:
            await self.task_state.set_status(file_md5, "failed")
            raise
        finally:
            self.reader.cleanup(read_result.file_path)

    def _flush_batch(self, records: list[ChunkRecord]) -> int:
        # TODO: 这里还有问题。目前 add_documents() 返回但是 bool 值，需要改成返回 embedding_id 列表。方便后续关联到 rag_chunks 表中。
        if self.vector_store is not None:
            ids = self.vector_store.add_documents(records)
        else:
            ids = []

        RagChunksCRUD.create_chunks(
            self.db,
            file_id=records[0].file_id if records else 0,
            chunks=records,
            embedding_ids=[str(item) for item in ids],
        )
        return len(records)
