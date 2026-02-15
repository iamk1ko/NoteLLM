from __future__ import annotations

import json

from minio import Minio
from redis.asyncio import Redis
from sqlalchemy.orm import Session
from unstructured.documents.elements import Element

from app.core.logging import get_logger
from app.crud.file_storage_crud import FileStorageCRUD
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
            chunk_size: int = 1000,
            overlap: int = 200,
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
        """
        向量化文件的主流程：
        1. 检查任务状态，如果已成功完成则跳过。
        2. 设置任务状态为 running。
        3. 从 MinIO 下载文件到本地。
        4. 解析文件内容为 Element 列表。
        5. 对 Element 列表进行切片，生成 TextChunk。
        6. 批量将切片记录写入向量数据库和关联表，并更新任务状态中的游标位置。
        7. 更新文件状态为 EMBEDDED，设置任务状态为 success。

        Args:
            file_id: 文件ID，对应 file_storage 表的主键。
            file_md5: 文件的MD5值，用于幂等性检查和任务状态管理。
            bucket_name: MinIO 存储桶名称。
            object_name: MinIO 对象名称（文件路径）。
            content_type: 文件的内容类型（MIME type），用于解析时选择合适的解析器。

        Returns:
            int: 成功向量化的切片总数。
        """

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
            # parse() 是调用 unstructured 的 partition_pdf()、partition_docx() 或 partition_md() 来解析文件，返回一个 Element 列表。
            elements: list[Element] = self.parser.parse(read_result.file_path, content_type)
            records: list[ChunkRecord] = []
            chunk_texts: list[str] = []

            # chunk_elements() 是调用 unstructured 的 chunk_by_title() 来对 Element 列表进行合并&切片，返回一个 TextChunk 生成器。每个 TextChunk 包含切片后的文本内容和相关的元数据。
            for chunk in self.chunker.chunk_elements(elements):
                if chunk.chunk_index <= last_chunk_index:
                    continue
                chunk_texts.append(chunk.chunk_text)
                records.append(
                    ChunkRecord(
                        file_id=file_id,
                        file_md5=file_md5,
                        content=chunk.chunk_text,
                        chunk_index=chunk.chunk_index,
                        chunk_size=chunk.chunk_size,
                        page_no=chunk.metadata.page_number,
                        section=chunk.metadata.page_title,
                        metadata=chunk.metadata
                    )
                )

                # 达到批量处理的阈值后，调用 _flush_batch() 将当前批次的切片记录写入向量数据库和关联表，并更新任务状态中的游标位置。然后清空当前批次的记录和文本列表，继续处理下一批切片。
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
        except Exception as e:
            logger.error("向量化任务失败：file_md5={}, error={}", file_md5, e)
            await self.task_state.set_status(file_md5, "failed")
            raise
        finally:
            self.reader.cleanup(read_result.file_path)

    def _flush_batch(self, records: list[ChunkRecord]) -> int:
        if self.vector_store is not None:
            if not self.vector_store.add_documents(records):
                logger.error("当前批量的 RAG 分片写入向量数据库失败，总共 {} 条分片记录", len(records))
                raise RuntimeError("批量写入向量数据库失败")
            logger.info("当前批量的 RAG 分片成功写入向量数据库，总共 {} 条分片记录", len(records))
        else:
            logger.warning("未配置向量数据库，当前批量的 RAG 分片将不会被写入向量数据库，总共 {} 条分片记录",
                           len(records))

        return len(records)
