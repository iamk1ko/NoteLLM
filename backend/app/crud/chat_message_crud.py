from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger

from app.models import ChatMessage

logger = get_logger(__name__)


class ChatMessageCRUD:
    """聊天消息相关的数据库操作（Repository/DAO 层）。

    说明：
    - 负责 chat_message 表的 CRUD 操作
    - 支持分页查询、按会话过滤、按角色过滤
    - 用于查询消息历史和保存用户/AI 消息

    使用示例：
        ```python
        # 创建用户消息
        message = await ChatMessageCRUD.create_message_async(
            db=session,
            session_id=1,
            user_id=1,
            content="你好，请介绍一下RAG",
            role="user"
        )

        # 创建 AI 回复消息
        ai_message = await ChatMessageCRUD.create_message_async(
            db=session,
            session_id=1,
            user_id=1,
            content="RAG是...",
            role="assistant",
            model_name="qwen2.5:0.6b"
        )

        # 查询会话的消息列表
        messages, total = await ChatMessageCRUD.get_session_messages_async(
            db=session,
            session_id=1,
            page=1,
            size=20
        )
        ```
    """

    @staticmethod
    async def create_message_async(
        db: AsyncSession,
        session_id: int,
        user_id: int,
        content: str,
        role: str = "user",
        model_name: str | None = None,
        token_count: int | None = None,
    ) -> ChatMessage:
        """异步创建聊天消息。"""

        message = ChatMessage(
            session_id=session_id,
            user_id=user_id,
            content=content,
            role=role,
            model_name=model_name,
            token_count=token_count,
        )

        db.add(message)
        await db.commit()
        await db.refresh(message)

        logger.debug(
            "异步创建聊天消息：message_id={}, session_id={}, user_id={}, role={}",
            message.id,
            session_id,
            user_id,
            role,
        )

        return message

    @staticmethod
    async def get_session_messages_async(
        db: AsyncSession,
        session_id: int,
        page: int = 1,
        size: int = 20,
        role: str | None = None,
    ) -> tuple[Sequence[ChatMessage], int]:
        """查询会话的消息列表（分页，异步版）。"""

        stmt = select(ChatMessage).where(ChatMessage.session_id == session_id)

        if role:
            stmt = stmt.where(ChatMessage.role == role)

        # 查询总数
        count_stmt = select(func.count(ChatMessage.id)).where(
            ChatMessage.session_id == session_id
        )
        if role:
            count_stmt = count_stmt.where(ChatMessage.role == role)

        total = (await db.scalar(count_stmt)) or 0

        # 分页查询
        stmt = stmt.order_by(ChatMessage.id.asc()).offset((page - 1) * size).limit(size)

        result = await db.execute(stmt)
        messages = result.scalars().all()

        logger.debug(
            "查询会话消息列表(Async)：session_id={}, total={}, page={}, size={}",
            session_id,
            total,
            page,
            size,
        )

        return messages, total

    @staticmethod
    async def get_recent_messages_async(
        db: AsyncSession, session_id: int, limit: int = 10
    ) -> Sequence[ChatMessage]:
        """获取会话的最近 N 条消息（异步版）。"""

        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.id.desc())
            .limit(limit)
        )
        messages = result.scalars().all()

        # 按时间升序返回（最早的在前）
        messages = list(reversed(messages))

        logger.debug(
            "获取会话最近消息(Async)：session_id={}, limit={}, count={}",
            session_id,
            limit,
            len(messages),
        )

        return messages

    @staticmethod
    async def get_messages_after_async(
        db: AsyncSession, session_id: int, after_message_id: int, limit: int = 100
    ) -> Sequence[ChatMessage]:
        """获取会话中某条消息之后的所有消息（异步版）。"""

        result = await db.execute(
            select(ChatMessage)
            .where(
                and_(
                    ChatMessage.session_id == session_id,
                    ChatMessage.id > after_message_id,
                )
            )
            .order_by(ChatMessage.id.asc())
            .limit(limit)
        )
        messages = result.scalars().all()

        logger.debug(
            "获取会话增量消息(Async)：session_id={}, after_id={}, count={}",
            session_id,
            after_message_id,
            len(messages),
        )

        return messages

    @staticmethod
    async def get_message_by_id_async(
        db: AsyncSession, message_id: int
    ) -> ChatMessage | None:
        """根据 ID 获取消息（异步版）。"""
        return await db.get(ChatMessage, message_id)

    @staticmethod
    async def get_user_session_messages_async(
        db: AsyncSession,
        session_id: int,
        user_id: int,
        page: int = 1,
        size: int = 20,
    ) -> tuple[Sequence[ChatMessage], int]:
        """获取用户在某个会话中的消息列表（带权限检查，异步版）。"""

        stmt = select(ChatMessage).where(
            and_(ChatMessage.session_id == session_id, ChatMessage.user_id == user_id)
        )

        # 查询总数
        count_stmt = select(func.count(ChatMessage.id)).where(
            and_(ChatMessage.session_id == session_id, ChatMessage.user_id == user_id)
        )

        total = (await db.scalar(count_stmt)) or 0

        # 分页查询
        stmt = stmt.order_by(ChatMessage.id.asc()).offset((page - 1) * size).limit(size)

        result = await db.execute(stmt)
        messages = result.scalars().all()

        logger.debug(
            "查询用户会话消息(Async)：session_id={}, user_id={}, total={}, page={}, size={}",
            session_id,
            user_id,
            total,
            page,
            size,
        )

        return messages, total

    @staticmethod
    async def delete_session_messages_async(db: AsyncSession, session_id: int) -> int:
        """删除会话的所有消息（异步版）。"""
        from sqlalchemy import delete

        count_stmt = select(func.count(ChatMessage.id)).where(
            ChatMessage.session_id == session_id
        )
        count = (await db.scalar(count_stmt)) or 0

        await db.execute(
            delete(ChatMessage).where(ChatMessage.session_id == session_id)
        )
        await db.commit()

        logger.info(
            "删除会话的所有消息(Async)：session_id={}, count={}", session_id, count
        )

        return count
