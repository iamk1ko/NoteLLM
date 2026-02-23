from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import and_, func, or_, select, delete
from sqlalchemy.orm import Session, joinedload
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
        session = ChatSessionCRUD.create_session(
            db=session,
            user_id=1,
            title="新对话",
            biz_type="ai_chat"
        )

        # 查询用户的会话列表
        sessions, total = ChatSessionCRUD.get_user_sessions(
            db=session,
            user_id=1,
            page=1,
            size=10
        )

        # 获取会话详情（包含关联文件数量）
        session_detail = ChatSessionCRUD.get_session_with_file_count(
            db=session,
            session_id=1
        )
        ```
    """

    @staticmethod
    def create_session(
            db: Session,
            user_id: int,
            title: str | None = None,
            biz_type: str = "ai_chat",
            context_id: str | None = None,
    ) -> ChatSession:
        """创建新的聊天会话。

        参数说明：
        - db: 数据库会话
        - user_id: 用户 ID
        - title: 会话标题（可选）
        - biz_type: 业务类型（默认 "ai_chat"）
        - context_id: 外部上下文 ID（可选）

        返回值：
        - ChatSession: 创建成功的会话对象

        注意事项：
        - 不检查用户是否存在（由调用方确保）
        - 不处理权限检查（由调用方确保）
        """

        session = ChatSession(
            user_id=user_id,
            title=title,
            biz_type=biz_type,
            context_id=context_id,
            status=1,
        )

        db.add(session)
        db.commit()
        db.refresh(session)

        logger.info(
            "创建聊天会话成功：session_id={}, user_id={}, title={}",
            session.id,
            user_id,
            title,
        )

        return session

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
    def get_user_sessions(
            db: Session,
            user_id: int,
            page: int = 1,
            size: int = 10,
            biz_type: str | None = None,
    ) -> tuple[Sequence[ChatSession], int]:
        """查询用户的聊天会话列表（分页）。

        参数说明：
        - db: 数据库会话
        - user_id: 用户 ID
        - page: 页码（从 1 开始）
        - size: 每页数量
        - biz_type: 业务类型过滤（可选）

        返回值：
        - tuple: (会话列表, 总数量)

        注意事项：
        - 按 id 倒序排列（最新会话在前）
        - 只返回 status=1 的会话（进行中的会话）
        - 不包含已删除的会话
        """

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

        total = db.scalar(count_stmt) or 0

        # 分页查询
        stmt = (
            stmt.order_by(ChatSession.id.desc()).offset((page - 1) * size).limit(size)
        )

        sessions = db.scalars(stmt).all()

        logger.debug(
            "查询用户会话列表：user_id={}, total={}, page={}, size={}",
            user_id,
            total,
            page,
            size,
        )

        return sessions, total

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
    def get_all_sessions(
            db: Session,
            page: int = 1,
            size: int = 10,
            biz_type: str | None = None,
    ) -> tuple[Sequence[ChatSession], int]:
        """查询所有会话（管理员使用，分页）。

        说明：
        - 不限制 user_id，管理员可查看全部会话
        - 可选按 biz_type 过滤
        """

        stmt = select(ChatSession)
        count_stmt = select(func.count(ChatSession.id))

        if biz_type:
            stmt = stmt.where(ChatSession.biz_type == biz_type)
            count_stmt = count_stmt.where(ChatSession.biz_type == biz_type)

        total = db.scalar(count_stmt) or 0
        stmt = (
            stmt.order_by(ChatSession.id.desc()).offset((page - 1) * size).limit(size)
        )
        sessions = db.scalars(stmt).all()
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
    def get_session_by_id(db: Session, session_id: int) -> ChatSession | None:
        """根据 ID 获取聊天会话。

        参数说明：
        - db: 数据库会话
        - session_id: 会话 ID

        返回值：
        - ChatSession | None: 会话对象或 None（不存在）

        注意事项：
        - 不进行权限检查（由调用方确保）
        - 可以查询任意状态的会话
        """

        session = db.get(ChatSession, session_id)
        return session

    @staticmethod
    async def get_session_by_id_async(
            db: AsyncSession, session_id: int
    ) -> ChatSession | None:
        """根据 ID 获取聊天会话（异步版）。"""
        return await db.get(ChatSession, session_id)

    @staticmethod
    def get_user_session(
            db: Session, session_id: int, user_id: int
    ) -> ChatSession | None:
        """获取用户的聊天会话（带权限检查）。

        参数说明：
        - db: 数据库会话
        - session_id: 会话 ID
        - user_id: 用户 ID

        返回值：
        - ChatSession | None: 会话对象或 None（不存在或无权限）

        注意事项：
        - 会检查会话是否属于该用户
        - 管理员需要使用 get_session_by_id 方法
        - 此方法用于普通用户访问自己的会话
        """

        session = db.scalar(
            select(ChatSession).where(
                and_(ChatSession.id == session_id, ChatSession.user_id == user_id)
            )
        )
        return session

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
    def update_session(
            db: Session, session_id: int, update_data: dict[str, Any]
    ) -> ChatSession | None:
        """更新聊天会话信息。

        参数说明：
        - db: 数据库会话
        - session_id: 会话 ID
        - update_data: 更新数据字典

        返回值：
        - ChatSession | None: 更新后的会话对象或 None（不存在）

        注意事项：
        - 只更新提供的字段
        - 不检查权限（由调用方确保）
        - 支持的字段：title, status, context_id
        """

        session = db.get(ChatSession, session_id)
        if not session:
            return None

        for key, value in update_data.items():
            if hasattr(session, key):
                setattr(session, key, value)

        db.commit()
        db.refresh(session)

        logger.info(
            "更新聊天会话：session_id={}, update_data={}", session_id, update_data
        )

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
    def get_session_with_file_count(
            db: Session, session_id: int
    ) -> tuple[ChatSession | None, int]:
        """获取会话详情（包含关联文件数量）。

        参数说明：
        - db: 数据库会话
        - session_id: 会话 ID

        返回值：
        - tuple: (会话对象, 关联文件数量)

        注意事项：
        - 文件数量通过 JOIN chat_session_files 表统计
        - 不包含已删除的文件
        - 用于会话列表显示关联文件数量
        """

        session = db.scalar(select(ChatSession).where(ChatSession.id == session_id))

        if not session:
            return None, 0

        # 统计关联文件数量
        file_count = (
                db.scalar(
                    select(func.count(ChatSessionFile.id)).where(
                        ChatSessionFile.chat_session_id == session_id
                    )
                )
                or 0
        )

        return session, file_count

    @staticmethod
    async def get_session_with_file_count_async(
            db: AsyncSession, session_id: int
    ) -> tuple[ChatSession | None, int]:
        """获取会话详情（包含关联文件数量，异步版）。"""

        result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
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
    def link_file_to_session(
            db: Session, session_id: int, file_id: int
    ) -> ChatSessionFile | None:
        """关联文件到会话。

        参数说明：
        - db: 数据库会话
        - session_id: 会话 ID
        - file_id: 文件 ID

        返回值：
        - ChatSessionFile | None: 关联记录对象或 None（失败）

        注意事项：
        - 通过复合唯一索引避免重复关联
        - 不检查文件是否存在或权限（由调用方确保）
        - 不检查会话是否存在或权限（由调用方确保）
        """

        try:
            session_file = ChatSessionFile(chat_session_id=session_id, file_id=file_id)
            db.add(session_file)
            db.commit()
            db.refresh(session_file)

            logger.info(
                "关联文件到会话：session_id={}, file_id={}, relation_id={}",
                session_id,
                file_id,
                session_file.id,
            )

            return session_file

        except Exception as e:
            db.rollback()
            logger.error(
                "关联文件到会话失败：session_id={}, file_id={}, error={}",
                session_id,
                file_id,
                e,
            )
            return None

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
    def unlink_file_from_session(db: Session, session_id: int, file_id: int) -> bool:
        """取消文件与会话的关联。

        参数说明：
        - db: 数据库会话
        - session_id: 会话 ID
        - file_id: 文件 ID

        返回值：
        - bool: True 表示取消成功，False 表示关联不存在

        注意事项：
        - 只删除关联记录，不删除文件本身
        - 不检查权限（由调用方确保）
        """

        session_file = db.scalar(
            select(ChatSessionFile).where(
                and_(
                    ChatSessionFile.chat_session_id == session_id,
                    ChatSessionFile.file_id == file_id,
                )
            )
        )

        if not session_file:
            return False

        db.delete(session_file)
        db.commit()

        logger.info(
            "取消文件与会话关联：session_id={}, file_id={}",
            session_id,
            file_id,
        )

        return True

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
    def link_files_to_session(db: Session, session_id: int, file_ids: list[int]) -> int:
        """批量关联文件到会话。

        返回值：
        - int: 实际成功关联的数量
        """

        success = 0
        for file_id in file_ids:
            relation = ChatSessionCRUD.link_file_to_session(db, session_id, file_id)
            if relation:
                success += 1
        return success

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
    def unlink_files_from_session(
            db: Session, session_id: int, file_ids: list[int]
    ) -> int:
        """批量取消文件与会话的关联。

        返回值：
        - int: 实际取消关联的数量
        """

        success = 0
        for file_id in file_ids:
            if ChatSessionCRUD.unlink_file_from_session(db, session_id, file_id):
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
    def get_session_file_ids(db: Session, session_id: int) -> list[int]:
        """获取会话关联的所有文件 ID。

        参数说明：
        - db: 数据库会话
        - session_id: 会话 ID

        返回值：
        - list[int]: 文件 ID 列表

        注意事项：
        - 返回所有关联文件的 ID
        - 不检查文件是否存在或权限（由调用方确保）
        - 用于查询会话使用的知识库文件
        """

        file_ids = db.scalars(
            select(ChatSessionFile.file_id).where(
                ChatSessionFile.chat_session_id == session_id
            )
        ).all()

        return list(file_ids)

    @staticmethod
    async def get_session_file_ids_async(db: AsyncSession, session_id: int) -> list[int]:
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
