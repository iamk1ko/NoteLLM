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
    VectorizationError,
    VectorizationStage,
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
        await self.task_state.set_error(file_md5, "")
        await self.task_state.set_error_details(file_md5, None)
        cursor_raw = await self.task_state.get_cursor(file_md5)
        last_chunk_index = -1
        if cursor_raw:
            try:
                cursor = json.loads(cursor_raw)
                last_chunk_index = int(cursor.get("chunk_index", -1))
            except (ValueError, TypeError, json.JSONDecodeError):
                last_chunk_index = -1
        chunk_total: int = 0

        # TODO: 这里的流程还有优化空间。比如可以边下载边解析边切片，减少等待时间。目前的实现是先下载完整文件到本地，再进行解析和切片。
        try:
            await self.task_state.set_stage(file_md5, VectorizationStage.DOWNLOAD.value)
            read_result = self.reader.download(bucket_name, object_name)
        except Exception as e:
            error = VectorizationError(
                stage=VectorizationStage.DOWNLOAD,
                message=f"下载文件失败: bucket={bucket_name}, object={object_name}",
                code="download_failed",
                retryable=True,
                cause=e,
            )
            await self._mark_failed(file_md5, file_id, error)
            raise error from e
        try:
            # parse() 是调用 unstructured 的 partition_pdf()、partition_docx() 或 partition_md() 来解析文件，返回一个 Element 列表。
            try:
                await self.task_state.set_stage(
                    file_md5, VectorizationStage.PARSE.value
                )
                elements: list[Element] = self.parser.parse(
                    read_result.file_path, content_type
                )
            except Exception as e:
                raise VectorizationError(
                    stage=VectorizationStage.PARSE,
                    message=f"文档解析失败: content_type={content_type}",
                    code="parse_failed",
                    retryable=False,
                    cause=e,
                ) from e
            records: list[ChunkRecord] = []
            chunk_texts: list[str] = []

            # chunk_elements() 是调用 unstructured 的 chunk_by_title() 来对 Element 列表进行合并&切片，返回一个 TextChunk 生成器。每个 TextChunk 包含切片后的文本内容和相关的元数据。
            try:
                await self.task_state.set_stage(
                    file_md5, VectorizationStage.CHUNK.value
                )
                chunk_iter = self.chunker.chunk_elements(elements)
            except Exception as e:
                raise VectorizationError(
                    stage=VectorizationStage.CHUNK,
                    message="文本切分失败",
                    code="chunk_failed",
                    retryable=False,
                    cause=e,
                ) from e

            for chunk in chunk_iter:
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
                        page_no=chunk.metadata.page_number
                        if chunk.metadata is not None
                        else None,
                        section=chunk.metadata.page_title
                        if chunk.metadata is not None
                        else None,
                        metadata=chunk.metadata,
                    )
                )

                # 达到批量处理的阈值后，调用 _flush_batch() 将当前批次的切片记录写入向量数据库和关联表，并更新任务状态中的游标位置。然后清空当前批次的记录和文本列表，继续处理下一批切片。
                if len(chunk_texts) >= self.vector_batch_size:
                    await self.task_state.set_stage(
                        file_md5, VectorizationStage.STORE.value
                    )
                    chunk_total += await self._flush_batch(records)
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
                await self.task_state.set_stage(
                    file_md5, VectorizationStage.STORE.value
                )
                chunk_total += await self._flush_batch(records)
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
            await self.task_state.set_stage(file_md5, "success")
            return chunk_total
        except VectorizationError as e:
            logger.error(
                "向量化任务失败：file_md5={}, stage={}, error={}",
                file_md5,
                e.stage,
                e.message,
            )
            await self._mark_failed(file_md5, file_id, e)
            raise
        except Exception as e:
            logger.error("向量化任务失败：file_md5={}, error={}", file_md5, e)
            await self._mark_failed(file_md5, file_id, e)
            raise
        finally:
            self.reader.cleanup(read_result.file_path)

    async def _flush_batch(self, records: list[ChunkRecord]) -> int:
        if self.vector_store is not None:
            try:
                ok = await self.vector_store.add_documents(records)
            except Exception as e:
                raise VectorizationError(
                    stage=VectorizationStage.STORE,
                    message="向量写入失败",
                    code="store_failed",
                    retryable=True,
                    cause=e,
                ) from e
            if not ok:
                logger.error(
                    "当前批量的 RAG 分片写入向量数据库失败，总共 {} 条分片记录",
                    len(records),
                )
                raise RuntimeError("批量写入向量数据库失败")
            logger.info(
                "当前批量的 RAG 分片成功写入向量数据库，总共 {} 条分片记录",
                len(records),
            )
        else:
            logger.warning(
                "未配置向量数据库，当前批量的 RAG 分片将不会被写入向量数据库，总共 {} 条分片记录",
                len(records),
            )

        return len(records)

    async def _mark_failed(self, file_md5: str, file_id: int, error: Exception) -> None:
        await self.task_state.set_status(file_md5, "failed")
        if isinstance(error, VectorizationError):
            await self.task_state.set_error(
                file_md5, f"{error.stage}:{error.code}:{error.message}"
            )
            await self.task_state.set_error_details(file_md5, error)
        else:
            await self.task_state.set_error(file_md5, str(error))
            await self.task_state.set_error_details(file_md5, None)
        FileStorageCRUD.update_file_status(
            self.db, file_id=file_id, status=FileStorageStatus.FAILED.value
        )
