from __future__ import annotations

import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.crud.file_storage_crud import FileStorageCRUD
from app.models.file_storage import FileStorageStatus
from app.schemas import ChunkRecord
from app.services import MinioFileReader, DocumentParser, TextChunker, MilvusVectorStore
from app.services.vectorization.errors import VectorizationError, VectorizationStage
from app.services.vectorization.task_state import TaskStateStore

logger = get_logger(__name__)


class VectorizationOrchestrator:
    def __init__(
        self,
        *,
        db: AsyncSession,
        reader: MinioFileReader,
        parser: DocumentParser,
        chunker: TextChunker,
        vector_store: MilvusVectorStore | None,
        task_state: TaskStateStore,
        vector_batch_size: int = 64,
    ) -> None:
        self.db = db
        self.reader = reader
        self.parser = parser
        self.chunker = chunker
        self.vector_store = vector_store
        self.task_state = task_state
        self.vector_batch_size = vector_batch_size

    async def vectorize_file(
        self,
        *,
        file_id: int,
        file_md5: str,
        bucket_name: str,
        object_name: str,
        content_type: str,
    ) -> int:
        existing_status = await self.task_state.get_status(file_md5)
        if isinstance(existing_status, (bytes, bytearray)):
            existing_status = existing_status.decode("utf-8")
        if existing_status == "success":
            logger.info(
                "Redis 状态显示任务已完成，清理后重新执行：file_md5={}", file_md5
            )
            await self.task_state.clear(file_md5)

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

        # ================== 从 MinIO 中读取文件 ==================
        chunk_total = 0
        await self.task_state.set_stage(
            file_md5, VectorizationStage.DOWNLOAD.value
        )  # 设置当前阶段为下载 (从minio读取文件)
        try:
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
            # ================== 解析文件 ==================
            await self.task_state.set_stage(file_md5, VectorizationStage.PARSE.value)
            try:
                elements = self.parser.parse(read_result.file_path, content_type)
            except Exception as e:
                logger.error(
                    "文件解析失败: file_md5={}, content_type={}, error={}",
                    file_md5,
                    content_type,
                    e,
                )
                raise VectorizationError(
                    stage=VectorizationStage.PARSE,
                    message=f"文档解析失败: content_type={content_type}",
                    code="parse_failed",
                    retryable=False,
                    cause=e,
                ) from e

            # ==================== 通过标题划分文本 ==================
            await self.task_state.set_stage(file_md5, VectorizationStage.CHUNK.value)
            try:
                chunk_iter = self.chunker.chunk_elements_by_title(elements)
            except Exception as e:
                raise VectorizationError(
                    stage=VectorizationStage.CHUNK,
                    message="文本切分失败",
                    code="chunk_failed",
                    retryable=False,
                    cause=e,
                ) from e

            # ================== 批量写入向量数据库 ==================
            records: list[ChunkRecord] = []
            chunk_texts: list[str] = []

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

            # 向量化完成，更新文件状态和任务状态
            await FileStorageCRUD.update_file_status_async(
                self.db, file_id=file_id, status=FileStorageStatus.EMBEDDED.value
            )
            await self.task_state.set_status(file_md5, "success")
            await self.task_state.set_stage(file_md5, "success")
            # 成功后清理任务状态，避免下次上传同文件误判已完成
            await self.task_state.clear(file_md5)
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
        """将任务标记为失败，并记录错误信息。"""
        await self.task_state.set_status(file_md5, "failed")
        if isinstance(error, VectorizationError):
            await self.task_state.set_error(
                file_md5, f"{error.stage}:{error.code}:{error.message}"
            )
            await self.task_state.set_error_details(file_md5, error)
        else:
            await self.task_state.set_error(file_md5, str(error))
            await self.task_state.set_error_details(file_md5, None)
        await FileStorageCRUD.update_file_status_async(
            self.db, file_id=file_id, status=FileStorageStatus.FAILED.value
        )
        # 失败后不清理，保留错误信息便于排查；依赖 TTL 自动过期
