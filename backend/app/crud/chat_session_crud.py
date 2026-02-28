from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import and_, func, or_, select, delete
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models import ChatSession, ChatSessionFile, FileStorage

logger = get_logger(__name__)


class ChatSessionCRUD:
    """聊天会话相关的数据库操作（Repository/DAO 层）。

    说明：
    - 负责 chat_session 表的 CRUD 操作
    - 支持分页查询、按用户过滤、按业务类型过滤
    - 不处理业务逻辑和权限检查，由 Service 层负责

    使用示例：
        ```python
        # 创建会话
        session = await ChatSessionCRUD.create_session_async(
            db=session,
            user_id=1,
            title="新对话",
            biz_type="ai_chat"
        )

        # 查询用户的会话列表
        sessions, total = await ChatSessionCRUD.get_user_sessions_async(
            db=session,
            user_id=1,
            page=1,
            size=10
        )

        # 获取会话详情（包含关联文件数量）
        session_detail, file_count = await ChatSessionCRUD.get_session_with_file_count_async(
            db=session,
            session_id=1
        )
        ```
    """

    @staticmethod
    async def create_session_async(
        db: AsyncSession,
        user_id: int,
        title: str | None = None,
        biz_type: str = "ai_chat",
        context_id: str | None = None,
    ) -> ChatSession:
        """创建新的聊天会话（异步版）。"""

        session = ChatSession(
            user_id=user_id,
            title=title,
            biz_type=biz_type,
            context_id=context_id,
            status=1,
        )

        db.add(session)
        await db.commit()
        await db.refresh(session)

        logger.info(
            "创建聊天会话(Async)：session_id={}, user_id={}, title={}",
            session.id,
            user_id,
            title,
        )

        return session

    @staticmethod
    async def get_user_sessions_async(
        db: AsyncSession,
        user_id: int,
        page: int = 1,
        size: int = 10,
        biz_type: str | None = None,
    ) -> tuple[Sequence[ChatSession], int]:
        """查询用户的聊天会话列表（分页，异步版）。"""

        stmt = select(ChatSession).where(
            ChatSession.user_id == user_id, ChatSession.status == 1
        )

        if biz_type:
            stmt = stmt.where(ChatSession.biz_type == biz_type)

        # 查询总数
        count_stmt = select(func.count(ChatSession.id)).where(
            ChatSession.user_id == user_id, ChatSession.status == 1
        )
        if biz_type:
            count_stmt = count_stmt.where(ChatSession.biz_type == biz_type)

        total = (await db.scalar(count_stmt)) or 0

        # 分页查询
        stmt = (
            stmt.order_by(ChatSession.id.desc()).offset((page - 1) * size).limit(size)
        )

        result = await db.execute(stmt)
        sessions = result.scalars().all()

        logger.debug(
            "查询用户会话列表(Async)：user_id={}, total={}, page={}, size={}",
            user_id,
            total,
            page,
            size,
        )

        return sessions, total

    @staticmethod
    async def get_all_sessions_async(
        db: AsyncSession,
        page: int = 1,
        size: int = 10,
        biz_type: str | None = None,
    ) -> tuple[Sequence[ChatSession], int]:
        """查询所有会话（管理员使用，分页，异步版）。"""

        stmt = select(ChatSession)
        count_stmt = select(func.count(ChatSession.id))

        if biz_type:
            stmt = stmt.where(ChatSession.biz_type == biz_type)
            count_stmt = count_stmt.where(ChatSession.biz_type == biz_type)

        total = (await db.scalar(count_stmt)) or 0
        stmt = (
            stmt.order_by(ChatSession.id.desc()).offset((page - 1) * size).limit(size)
        )
        result = await db.execute(stmt)
        sessions = result.scalars().all()
        return sessions, total

    @staticmethod
    async def get_session_by_id_async(
        db: AsyncSession, session_id: int
    ) -> ChatSession | None:
        """根据 ID 获取聊天会话（异步版）。"""
        return await db.get(ChatSession, session_id)

    @staticmethod
    async def get_user_session_async(
        db: AsyncSession, session_id: int, user_id: int
    ) -> ChatSession | None:
        """获取用户的聊天会话（带权限检查，异步版）。"""

        result = await db.execute(
            select(ChatSession).where(
                and_(ChatSession.id == session_id, ChatSession.user_id == user_id)
            )
        )
        session = result.scalar_one_or_none()
        return session

    @staticmethod
    async def update_session_async(
        db: AsyncSession, session_id: int, update_data: dict[str, Any]
    ) -> ChatSession | None:
        """更新聊天会话信息（异步版）。"""

        session = await db.get(ChatSession, session_id)
        if not session:
            return None

        for key, value in update_data.items():
            if hasattr(session, key):
                setattr(session, key, value)

        await db.commit()
        await db.refresh(session)

        logger.info(
            "更新聊天会话(Async)：session_id={}, update_data={}",
            session_id,
            update_data,
        )

        return session

    @staticmethod
    async def delete_session_async(db: AsyncSession, session_id: int) -> bool:
        """删除聊天会话（异步版）。"""

        session = await db.get(ChatSession, session_id)
        if not session:
            return False

        await db.delete(session)
        await db.commit()

        logger.info("删除聊天会话(Async)：session_id={}", session_id)

        return True

    @staticmethod
    async def get_sessions_by_context_id_async(
        db: AsyncSession, context_id: str, user_id: int
    ) -> Sequence[ChatSession]:
        """异步获取指定 context_id 的所有会话（通常用于文件删除时清理关联会话）。

        参数说明：
        - db: 数据库会话
        - context_id: 外部上下文 ID（如文件 ID）
        - user_id: 用户 ID

        返回值：
        - Sequence[ChatSession]: 会话列表
        """
        result = await db.scalars(
            select(ChatSession).where(
                and_(
                    ChatSession.context_id == context_id,
                    ChatSession.user_id == user_id,
                    ChatSession.status == 1,
                )
            )
        )
        sessions = result.all()

        logger.debug(
            "通过 context_id 查询会话：context_id={}, user_id={}, count={}",
            context_id,
            user_id,
            len(sessions),
        )

        return sessions

    @staticmethod
    async def get_session_with_file_count_async(
        db: AsyncSession, session_id: int
    ) -> tuple[ChatSession | None, int]:
        """获取会话详情（包含关联文件数量，异步版）。"""

        result = await db.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        session = result.scalar_one_or_none()

        if not session:
            return None, 0

        # 统计关联文件数量
        count_stmt = select(func.count(ChatSessionFile.id)).where(
            ChatSessionFile.chat_session_id == session_id
        )
        file_count = (await db.scalar(count_stmt)) or 0

        return session, file_count

    @staticmethod
    async def link_file_to_session_async(
        db: AsyncSession, session_id: int, file_id: int
    ) -> ChatSessionFile | None:
        """关联文件到会话（异步版）。"""

        try:
            session_file = ChatSessionFile(chat_session_id=session_id, file_id=file_id)
            db.add(session_file)
            await db.commit()
            await db.refresh(session_file)

            logger.info(
                "关联文件到会话(Async)：session_id={}, file_id={}, relation_id={}",
                session_id,
                file_id,
                session_file.id,
            )

            return session_file

        except Exception as e:
            await db.rollback()
            logger.error(
                "关联文件到会话失败(Async)：session_id={}, file_id={}, error={}",
                session_id,
                file_id,
                e,
            )
            return None

    @staticmethod
    async def unlink_file_from_session_async(
        db: AsyncSession, session_id: int, file_id: int
    ) -> bool:
        """取消文件与会话的关联（异步版）。"""

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
            "取消文件与会话关联(Async)：session_id={}, file_id={}",
            session_id,
            file_id,
        )

        return True

    @staticmethod
    async def link_files_to_session_async(
        db: AsyncSession, session_id: int, file_ids: list[int]
    ) -> int:
        """批量关联文件到会话（异步版）。"""

        success = 0
        for file_id in file_ids:
            relation = await ChatSessionCRUD.link_file_to_session_async(
                db, session_id, file_id
            )
            if relation:
                success += 1
        return success

    @staticmethod
    async def unlink_files_from_session_async(
        db: AsyncSession, session_id: int, file_ids: list[int]
    ) -> int:
        """批量取消文件与会话的关联（异步版）。"""

        success = 0
        for file_id in file_ids:
            if await ChatSessionCRUD.unlink_file_from_session_async(
                db, session_id, file_id
            ):
                success += 1
        return success

    @staticmethod
    async def get_session_file_ids_async(
        db: AsyncSession, session_id: int
    ) -> list[int]:
        """获取会话关联的所有文件 ID（异步版）。"""

        result = await db.execute(
            select(ChatSessionFile.file_id).where(
                ChatSessionFile.chat_session_id == session_id
            )
        )
        file_ids = result.scalars().all()

        return list(file_ids)

    @staticmethod
    async def get_session_files_async(
        db: AsyncSession, session_id: int
    ) -> Sequence[FileStorage]:
        """获取会话关联的所有文件详情（异步版）。"""

        result = await db.execute(
            select(FileStorage)
            .join(ChatSessionFile, FileStorage.id == ChatSessionFile.file_id)
            .where(ChatSessionFile.chat_session_id == session_id)
            .where(FileStorage.status == 1)
        )
        files = result.scalars().all()

        return files
