from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import and_, func, select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models import ChatSessionFile

logger = get_logger(__name__)


class ChatSessionFileCRUD:
    """会话-文件关联相关的数据库操作（Repository/DAO 层）。

    说明：
    - 负责 chat_session_files 表的 CRUD 操作
    - 管理会话与文件的多对多关系
    - 支持批量操作和查询

    使用示例：
        ```python
        # 为会话添加文件
        await ChatSessionFileCRUD.add_files_to_session_async(
            db=session,
            session_id=1,
            file_ids=[10, 20, 30]
        )

        # 从会话中移除文件
        await ChatSessionFileCRUD.remove_files_from_session_async(
            db=session,
            session_id=1,
            file_ids=[10, 20]
        )

        # 查询会话关联的所有文件 ID
        file_ids = await ChatSessionFileCRUD.get_session_file_ids_async(
            db=session,
            session_id=1
        )

        # 查询文件被哪些会话使用
        session_ids = await ChatSessionFileCRUD.get_file_session_ids_async(
            db=session,
            file_id=10
        )

        # 检查文件是否在会话中
        exists = await ChatSessionFileCRUD.check_file_in_session_async(
            db=session,
            session_id=1,
            file_id=10
        )
        ```
    """

    @staticmethod
    async def add_file_to_session_async(
        db: AsyncSession, session_id: int, file_id: int
    ) -> ChatSessionFile | None:
        """为会话添加文件（异步）。"""

        try:
            session_file = ChatSessionFile(chat_session_id=session_id, file_id=file_id)
            db.add(session_file)
            await db.commit()
            await db.refresh(session_file)

            logger.info(
                "为会话添加文件：session_id={}, file_id={}, relation_id={}",
                session_id,
                file_id,
                session_file.id,
            )

            return session_file
        except Exception as e:
            await db.rollback()
            logger.error(
                "为会话添加文件失败：session_id={}, file_id={}, error={}",
                session_id,
                file_id,
                e,
            )
            return None

    @staticmethod
    async def add_files_to_session_async(
        db: AsyncSession, session_id: int, file_ids: Sequence[int]
    ) -> int:
        """为会话批量添加文件（异步）。"""

        for file_id in file_ids:
            session_file = ChatSessionFile(chat_session_id=session_id, file_id=file_id)
            db.add(session_file)

        try:
            await db.commit()

            result = await db.scalar(
                select(func.count(ChatSessionFile.id)).where(
                    ChatSessionFile.chat_session_id == session_id
                )
            )
            success_count = result or 0

            logger.info(
                "为会话批量添加文件：session_id={}, success_count={}",
                session_id,
                success_count,
            )

            return success_count
        except Exception as e:
            await db.rollback()
            logger.error(
                "为会话批量添加文件失败：session_id={}, file_ids={}, error={}",
                session_id,
                file_ids,
                e,
            )
            return 0

    @staticmethod
    async def remove_file_from_session_async(
        db: AsyncSession, session_id: int, file_id: int
    ) -> bool:
        """从会话中移除文件（异步）。"""

        result = await db.execute(
            select(ChatSessionFile).where(
                and_(
                    ChatSessionFile.chat_session_id == session_id,
                    ChatSessionFile.file_id == file_id,
                )
            )
        )
        session_file = result.scalar_one_or_none()
        if not session_file:
            return False

        await db.delete(session_file)
        await db.commit()

        logger.info(
            "从会话中移除文件：session_id={}, file_id={}",
            session_id,
            file_id,
        )

        return True

    @staticmethod
    async def remove_files_from_session_async(
        db: AsyncSession, session_id: int, file_ids: Sequence[int]
    ) -> int:
        """从会话中批量移除文件（异步）。"""

        count = (
            await db.scalar(
                select(func.count(ChatSessionFile.id)).where(
                    and_(
                        ChatSessionFile.chat_session_id == session_id,
                        ChatSessionFile.file_id.in_(file_ids),
                    )
                )
            )
            or 0
        )

        if count == 0:
            return 0

        await db.execute(
            delete(ChatSessionFile).where(
                and_(
                    ChatSessionFile.chat_session_id == session_id,
                    ChatSessionFile.file_id.in_(file_ids),
                )
            )
        )
        await db.commit()

        logger.info(
            "从会话中批量移除文件：session_id={}, count={}",
            session_id,
            count,
        )

        return count

    @staticmethod
    async def get_session_file_ids_async(
        db: AsyncSession, session_id: int
    ) -> Sequence[int]:
        """获取会话关联的所有文件 ID（异步）。"""

        result = await db.scalars(
            select(ChatSessionFile.file_id).where(
                ChatSessionFile.chat_session_id == session_id
            )
        )
        file_ids = result.all()

        logger.debug(
            "查询会话关联文件 ID：session_id={}, count={}",
            session_id,
            len(file_ids),
        )

        return file_ids

    @staticmethod
    async def get_file_session_ids_async(
        db: AsyncSession, file_id: int
    ) -> Sequence[int]:
        """获取文件被哪些会话使用（异步）。"""

        result = await db.scalars(
            select(ChatSessionFile.chat_session_id).where(
                ChatSessionFile.file_id == file_id
            )
        )
        session_ids = result.all()

        logger.debug(
            "查询文件使用的会话 ID（异步）：file_id={}, count={}",
            file_id,
            len(session_ids),
        )

        return session_ids

    @staticmethod
    async def check_file_in_session_async(
        db: AsyncSession, session_id: int, file_id: int
    ) -> bool:
        """检查文件是否在会话中（异步）。"""

        exists = await db.scalar(
            select(func.count(ChatSessionFile.id)).where(
                and_(
                    ChatSessionFile.chat_session_id == session_id,
                    ChatSessionFile.file_id == file_id,
                )
            )
        )

        return (exists or 0) > 0

    @staticmethod
    async def remove_all_files_from_session_async(
        db: AsyncSession, session_id: int
    ) -> int:
        """移除会话的所有文件关联（异步）。"""

        count = (
            await db.scalar(
                select(func.count(ChatSessionFile.id)).where(
                    ChatSessionFile.chat_session_id == session_id
                )
            )
            or 0
        )

        if count == 0:
            return 0

        await db.execute(
            delete(ChatSessionFile).where(ChatSessionFile.chat_session_id == session_id)
        )
        await db.commit()

        logger.info(
            "移除会话的所有文件关联：session_id={}, count={}",
            session_id,
            count,
        )

        return count

    @staticmethod
    async def remove_session_from_all_files_async(
        db: AsyncSession, session_id: int
    ) -> int:
        """移除会话与所有文件的关联（异步）。"""

        return await ChatSessionFileCRUD.remove_all_files_from_session_async(
            db, session_id
        )
