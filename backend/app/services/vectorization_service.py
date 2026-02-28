from __future__ import annotations

from minio import Minio
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.vectorization import (
    DocumentParser,
    MinioFileReader,
    TaskStateStore,
    TextChunker,
    MilvusVectorStore,
)
from app.services.vectorization.orchestrator import VectorizationOrchestrator


class VectorizationService:
    def __init__(
        self,
        db: AsyncSession,
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
        self.orchestrator = VectorizationOrchestrator(
            db=db,
            reader=self.reader,
            parser=self.parser,
            chunker=self.chunker,
            vector_store=self.vector_store,
            task_state=self.task_state,
            vector_batch_size=self.vector_batch_size,
        )

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

        return await self.orchestrator.vectorize_file(
            file_id=file_id,
            file_md5=file_md5,
            bucket_name=bucket_name,
            object_name=object_name,
            content_type=content_type,
        )
