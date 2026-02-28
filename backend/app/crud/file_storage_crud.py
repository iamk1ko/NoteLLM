from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import and_, func, or_, select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models import FileStorage, ChatSessionFile, FileStorageStatus

logger = get_logger(__name__)


class FileStorageCRUD:
    """文件存储相关的数据库操作（Repository/DAO 层）。

    说明：
    - 负责 file_storage 表的 CRUD 操作
    - 支持分页查询、按用户过滤、按可见性过滤
    - 用于管理用户上传的文件和公共文件

    使用示例：
        ```python
        # 创建文件记录
        file = await FileStorageCRUD.create_file_async(
            db=session,
            user_id=1,
            filename="document.pdf",
            content_type="application/pdf",
            file_size=1024000,
            bucket_name="user-files",
            object_name="user1/document.pdf",
            is_public=False
        )

        # 查询用户的文件列表（含公共文件）
        files, total = await FileStorageCRUD.get_user_files_async(
            db=session,
            user_id=1,
            page=1,
            size=10,
            include_public=True
        )

        # 查询公共文件
        public_files, total = await FileStorageCRUD.get_public_files_async(
            db=session,
            page=1,
            size=10
        )
        ```
    """

    @staticmethod
    async def create_file_async(
        db: AsyncSession,
        user_id: int,
        filename: str,
        content_type: str,
        file_size: int,
        bucket_name: str,
        object_name: str,
        etag: str | None = None,
        is_public: bool = False,
        status: int = 1,
    ) -> FileStorage:
        """异步创建文件存储记录。"""

        file_storage = FileStorage(
            user_id=user_id,
            filename=filename,
            content_type=content_type,
            file_size=file_size,
            bucket_name=bucket_name,
            object_name=object_name,
            etag=etag,
            is_public=is_public,
            status=status,
        )

        db.add(file_storage)
        await db.commit()
        await db.refresh(file_storage)

        logger.info(
            "异步创建文件存储记录：file_id={}, user_id={}, filename={}, is_public={}",
            file_storage.id,
            user_id,
            filename,
            is_public,
        )

        return file_storage

    @staticmethod
    async def get_user_files_async(
        db: AsyncSession,
        user_id: int,
        page: int = 1,
        size: int = 10,
        include_public: bool = True,
        keyword: str | None = None,
        status: int | None = None,
        content_type: str | None = None,
    ) -> tuple[Sequence[FileStorage], int]:
        """异步查询用户的文件列表（分页，可包含公共文件）。"""

        # 构建查询条件：用户自己的文件 或 公共文件
        conditions = [
            or_(
                FileStorage.user_id == user_id,
                FileStorage.is_public == True,
            )
            if include_public
            else FileStorage.user_id == user_id
        ]

        if keyword:
            like = f"%{keyword}%"
            conditions.append(FileStorage.filename.like(like))

        if status is not None:
            conditions.append(FileStorage.status == status)

        if content_type:
            conditions.append(FileStorage.content_type == content_type)

        stmt = select(FileStorage).where(and_(*conditions))

        # 查询总数
        count_stmt = select(func.count(FileStorage.id)).where(and_(*conditions))

        total = await db.scalar(count_stmt) or 0

        # 分页查询
        stmt = (
            stmt.order_by(FileStorage.id.desc()).offset((page - 1) * size).limit(size)
        )

        result = await db.scalars(stmt)
        files = result.all()

        logger.debug(
            "异步查询用户文件列表：user_id={}, total={}, page={}, size={}",
            user_id,
            total,
            page,
            size,
        )

        return files, total

    @staticmethod
    async def get_file_by_id_async(
        db: AsyncSession, file_id: int
    ) -> FileStorage | None:
        """异步根据 ID 获取文件。"""
        return await db.get(FileStorage, file_id)

    @staticmethod
    async def get_file_by_object_name_async(
        db: AsyncSession, user_id: int, object_name: str
    ) -> FileStorage | None:
        """异步通过对象名称查询文件记录。"""

        result = await db.scalar(
            select(FileStorage).where(
                FileStorage.user_id == user_id,
                FileStorage.object_name == object_name,
            )
        )
        return result

    @staticmethod
    async def get_user_file_by_md5_async(
        db: AsyncSession, user_id: int, file_md5: str
    ) -> FileStorage | None:
        """根据用户与文件 MD5 查询文件记录。"""

        result = await db.scalar(
            select(FileStorage).where(
                and_(
                    FileStorage.user_id == user_id,
                    FileStorage.etag == file_md5,
                )
            )
        )
        return result

    @staticmethod
    async def update_file_upload_complete_async(
        db: AsyncSession,
        file_id: int,
        bucket_name: str,
        object_name: str,
        status: int,
    ) -> None:
        """异步更新文件合并后的存储信息与状态。"""

        file_obj = await db.get(FileStorage, file_id)
        if not file_obj:
            return
        file_obj.bucket_name = bucket_name
        file_obj.object_name = object_name
        file_obj.status = status
        await db.commit()

    @staticmethod
    async def get_user_file_async(
        db: AsyncSession, file_id: int, user_id: int
    ) -> FileStorage | None:
        """异步获取用户的文件（带权限检查）。

        注意：
        - 不再限制 status == EMBEDDED，允许查询上传中或处理中的文件
        """

        result = await db.scalar(
            select(FileStorage).where(
                and_(
                    FileStorage.id == file_id,
                    # FileStorage.status == FileStorageStatus.EMBEDDED, # Remove this restriction
                    or_(
                        FileStorage.user_id == user_id,  # 用户的私有文件
                        FileStorage.is_public == True,  # 公共文件
                    ),
                )
            )
        )
        return result

    @staticmethod
    async def get_public_files_async(
        db: AsyncSession, page: int = 1, size: int = 10
    ) -> tuple[Sequence[FileStorage], int]:
        """异步查询公共文件列表（分页）。"""

        stmt = select(FileStorage).where(
            and_(
                FileStorage.is_public == True,
                FileStorage.status == FileStorageStatus.EMBEDDED,
            )
        )

        # 查询总数
        count_stmt = select(func.count(FileStorage.id)).where(
            and_(
                FileStorage.is_public == True,
                FileStorage.status == FileStorageStatus.EMBEDDED,
            )
        )
        total = (await db.scalar(count_stmt)) or 0

        # 分页查询
        stmt = (
            stmt.order_by(FileStorage.id.desc()).offset((page - 1) * size).limit(size)
        )

        result = await db.scalars(stmt)
        files = result.all()

        logger.debug(
            "异步查询公共文件列表：total={}, page={}, size={}", total, page, size
        )

        return files, total

    @staticmethod
    async def list_files_by_status_async(
        db: AsyncSession, status: int, limit: int = 1000, offset: int = 0
    ) -> Sequence[FileStorage]:
        """按状态列出文件列表（不做权限过滤）。"""

        stmt = (
            select(FileStorage)
            .where(FileStorage.status == status)
            .order_by(FileStorage.id.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await db.scalars(stmt)
        return result.all()

    @staticmethod
    async def update_file_status_async(
        db: AsyncSession, file_id: int, status: int
    ) -> FileStorage | None:
        """异步更新文件状态。"""

        file = await db.get(FileStorage, file_id)
        if not file:
            return None

        file.status = status
        await db.commit()
        await db.refresh(file)

        logger.info("异步更新文件状态：file_id={}, status={}", file_id, status)

        return file

    @staticmethod
    async def delete_file_async(db: AsyncSession, file_id: int) -> bool:
        """异步删除文件（硬删除）。"""

        file = await db.get(FileStorage, file_id)
        if not file:
            return False

        # 先删除与会话的关联记录
        await db.execute(
            delete(ChatSessionFile).where(ChatSessionFile.file_id == file_id)
        )

        # 再删除文件记录
        await db.delete(file)
        await db.commit()

        logger.info("异步删除文件：file_id={}", file_id)

        return True
