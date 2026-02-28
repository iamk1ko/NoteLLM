from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import and_, func, select, delete, update
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models import FileChunks

logger = get_logger(__name__)


class FileChunksCRUD:
    """文件分片（上传分片）相关数据库操作。

    说明：
    - 负责 file_chunks 表的增删改查
    - 用于记录分片元信息与上传状态
    """

    @staticmethod
    def create_chunk(
        db: Session,
        file_md5: str,
        chunk_index: int,
        chunk_size: int,
        bucket_name: str,
        object_name: str,
        etag: str | None = None,
        status: int = 0,
    ) -> FileChunks:
        """创建分片记录（状态默认 0-上传中）。"""

        existing = FileChunksCRUD.get_chunk(db, file_md5, chunk_index)
        if existing:
            return existing

        chunk = FileChunks(
            # file_id=None, # NOTE: 原本设想 `所属文件ID（合并成功后回填）`。但是实际合并后，所有分片直接删除，根本不会用到这个字段，待优化。
            file_md5=file_md5,
            chunk_index=chunk_index,
            chunk_size=chunk_size,
            bucket_name=bucket_name,
            object_name=object_name,
            etag=etag,
            status=status,
        )
        db.add(chunk)
        db.commit()
        db.refresh(chunk)
        return chunk

    @staticmethod
    async def create_chunk_async(
        db: AsyncSession,
        file_md5: str,
        chunk_index: int,
        chunk_size: int,
        bucket_name: str,
        object_name: str,
        etag: str | None = None,
        status: int = 0,
    ) -> FileChunks:
        """异步创建分片记录（状态默认 0-上传中）。"""

        existing = await FileChunksCRUD.get_chunk_async(db, file_md5, chunk_index)
        if existing:
            return existing

        chunk = FileChunks(
            file_md5=file_md5,
            chunk_index=chunk_index,
            chunk_size=chunk_size,
            bucket_name=bucket_name,
            object_name=object_name,
            etag=etag,
            status=status,
        )
        db.add(chunk)
        await db.commit()
        await db.refresh(chunk)
        return chunk

    @staticmethod
    def get_chunk(db: Session, file_md5: str, chunk_index: int) -> FileChunks | None:
        """获取指定分片记录。"""

        return db.scalar(
            select(FileChunks).where(
                and_(
                    FileChunks.file_md5 == file_md5,
                    FileChunks.chunk_index == chunk_index,
                )
            )
        )

    @staticmethod
    async def get_chunk_async(
        db: AsyncSession, file_md5: str, chunk_index: int
    ) -> FileChunks | None:
        """异步获取指定分片记录。"""

        return await db.scalar(
            select(FileChunks).where(
                and_(
                    FileChunks.file_md5 == file_md5,
                    FileChunks.chunk_index == chunk_index,
                )
            )
        )

    @staticmethod
    def update_chunk_etag(
        db: Session, file_md5: str, chunk_index: int, etag: str
    ) -> None:
        """更新分片的 ETag/MD5。"""

        chunk = FileChunksCRUD.get_chunk(db, file_md5, chunk_index)
        if not chunk:
            return
        chunk.etag = etag
        db.commit()

    @staticmethod
    async def update_chunk_etag_async(
        db: AsyncSession, file_md5: str, chunk_index: int, etag: str
    ) -> None:
        """异步更新分片的 ETag/MD5。"""

        chunk = await FileChunksCRUD.get_chunk_async(db, file_md5, chunk_index)
        if not chunk:
            return
        chunk.etag = etag
        await db.commit()

    @staticmethod
    def update_chunk_status(
        db: Session, file_md5: str, chunk_index: int, status: int
    ) -> None:
        """更新分片状态。"""

        chunk = db.scalar(
            select(FileChunks).where(
                and_(
                    FileChunks.file_md5 == file_md5,
                    FileChunks.chunk_index == chunk_index,
                )
            )
        )
        if not chunk:
            return
        chunk.status = status
        db.commit()

    @staticmethod
    async def update_chunk_status_async(
        db: AsyncSession, file_md5: str, chunk_index: int, status: int
    ) -> None:
        """异步更新分片状态。"""

        chunk = await db.scalar(
            select(FileChunks).where(
                and_(
                    FileChunks.file_md5 == file_md5,
                    FileChunks.chunk_index == chunk_index,
                )
            )
        )
        if not chunk:
            return
        chunk.status = status
        await db.commit()

    @staticmethod
    def set_file_id_for_md5(db: Session, file_md5: str, file_id: int) -> None:
        """合并成功后回填 file_id。"""

        db.query(FileChunks).filter(FileChunks.file_md5 == file_md5).update(
            {"file_id": file_id}
        )
        db.commit()

    @staticmethod
    def count_chunks(db: Session, file_md5: str) -> int:
        """统计分片数量。"""

        return (
            db.scalar(
                select(func.count(FileChunks.id)).where(FileChunks.file_md5 == file_md5)
            )
            or 0
        )

    @staticmethod
    async def count_chunks_async(db: AsyncSession, file_md5: str) -> int:
        """异步统计分片数量。"""

        return (
            await db.scalar(
                select(func.count(FileChunks.id)).where(FileChunks.file_md5 == file_md5)
            )
            or 0
        )

    @staticmethod
    def list_chunks(db: Session, file_md5: str) -> Sequence[FileChunks]:
        """列出所有分片（按 chunk_index 升序）。"""

        return db.scalars(
            select(FileChunks)
            .where(FileChunks.file_md5 == file_md5)
            .order_by(FileChunks.chunk_index.asc())
        ).all()

    @staticmethod
    async def list_chunks_async(
        db: AsyncSession, file_md5: str
    ) -> Sequence[FileChunks]:
        """异步列出所有分片（按 chunk_index 升序）。"""

        result = await db.scalars(
            select(FileChunks)
            .where(FileChunks.file_md5 == file_md5)
            .order_by(FileChunks.chunk_index.asc())
        )
        return result.all()

    @staticmethod
    def delete_chunks(db: Session, file_md5: str) -> int:
        """删除某个文件的所有分片记录。"""

        count = FileChunksCRUD.count_chunks(db, file_md5)
        db.query(FileChunks).filter(FileChunks.file_md5 == file_md5).delete()
        db.commit()
        return count

    @staticmethod
    async def delete_chunks_async(db: AsyncSession, file_md5: str) -> int:
        """异步删除某个文件的所有分片记录。"""

        count = await FileChunksCRUD.count_chunks_async(db, file_md5)
        await db.execute(delete(FileChunks).where(FileChunks.file_md5 == file_md5))
        await db.commit()
        return count
