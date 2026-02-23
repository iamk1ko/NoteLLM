from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session
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
        message = ChatMessageCRUD.create_message(
            db=session,
            session_id=1,
            user_id=1,
            content="你好，请介绍一下RAG",
            role="user"
        )

        # 创建 AI 回复消息
        ai_message = ChatMessageCRUD.create_message(
            db=session,
            session_id=1,
            user_id=1,
            content="RAG是...",
            role="assistant",
            model_name="qwen2.5:0.6b"
        )

        # 查询会话的消息列表
        messages, total = ChatMessageCRUD.get_session_messages(
            db=session,
            session_id=1,
            page=1,
            size=20
        )
        ```
    """

    @staticmethod
    def create_message(
        db: Session,
        session_id: int,
        user_id: int,
        content: str,
        role: str = "user",
        model_name: str | None = None,
        token_count: int | None = None,
    ) -> ChatMessage:
        """创建聊天消息。

        参数说明：
        - db: 数据库会话
        - session_id: 会话 ID
        - user_id: 用户 ID
        - content: 消息内容
        - role: 消息角色（user/assistant/system/tool）
        - model_name: 使用的模型名称（AI 消息使用）
        - token_count: 消息的 Token 数量（AI 消息使用）

        返回值：
        - ChatMessage: 创建成功的消息对象

        注意事项：
        - 不检查会话或用户是否存在（由调用方确保）
        - 不处理权限检查（由调用方确保）
        - model_name 和 token_count 主要用于 AI 回复消息
        """

        message = ChatMessage(
            session_id=session_id,
            user_id=user_id,
            content=content,
            role=role,
            model_name=model_name,
            token_count=token_count,
        )

        db.add(message)
        db.commit()
        db.refresh(message)

        logger.info(
            "创建聊天消息：message_id={}, session_id={}, user_id={}, role={}",
            message.id,
            session_id,
            user_id,
            role,
        )

        return message

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

        logger.info(
            "异步创建聊天消息：message_id={}, session_id={}, user_id={}, role={}",
            message.id,
            session_id,
            user_id,
            role,
        )

        return message

    @staticmethod
    def get_session_messages(
        db: Session,
        session_id: int,
        page: int = 1,
        size: int = 20,
        role: str | None = None,
    ) -> tuple[Sequence[ChatMessage], int]:
        """查询会话的消息列表（分页）。

        参数说明：
        - db: 数据库会话
        - session_id: 会话 ID
        - page: 页码（从 1 开始）
        - size: 每页数量
        - role: 消息角色过滤（可选）

        返回值：
        - tuple: (消息列表, 总数量)

        注意事项：
        - 按 id 升序排列（时间顺序）
        - 可以按角色过滤（如只查询 assistant 消息）
        - 用于展示对话历史
        """

        stmt = select(ChatMessage).where(ChatMessage.session_id == session_id)

        if role:
            stmt = stmt.where(ChatMessage.role == role)

        # 查询总数
        count_stmt = select(func.count(ChatMessage.id)).where(
            ChatMessage.session_id == session_id
        )
        if role:
            count_stmt = count_stmt.where(ChatMessage.role == role)

        total = db.scalar(count_stmt) or 0

        # 分页查询
        stmt = stmt.order_by(ChatMessage.id.asc()).offset((page - 1) * size).limit(size)

        messages = db.scalars(stmt).all()

        logger.debug(
            "查询会话消息列表：session_id={}, total={}, page={}, size={}",
            session_id,
            total,
            page,
            size,
        )

        return messages, total

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
    def get_recent_messages(
        db: Session, session_id: int, limit: int = 10
    ) -> Sequence[ChatMessage]:
        """获取会话的最近 N 条消息。

        参数说明：
        - db: 数据库会话
        - session_id: 会话 ID
        - limit: 消息数量（默认 10）

        返回值：
        - Sequence[ChatMessage]: 消息列表（按时间升序）

        注意事项：
        - 用于 AI 对话时提供历史上下文
        - 返回最新的 N 条消息（按时间升序）
        - 默认限制为 10 条消息（可根据需求调整）
        - 用于构建 LLM 的 Prompt 上下文
        """

        messages = db.scalars(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.id.desc())
            .limit(limit)
        ).all()

        # 按时间升序返回（最早的在前）
        messages = list(reversed(messages))

        logger.debug(
            "获取会话最近消息：session_id={}, limit={}, count={}",
            session_id,
            limit,
            len(messages),
        )

        return messages

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
    def get_messages_after(
        db: Session, session_id: int, after_message_id: int, limit: int = 100
    ) -> Sequence[ChatMessage]:
        """获取会话中某条消息之后的所有消息。

        参数说明：
        - db: 数据库会话
        - session_id: 会话 ID
        - after_message_id: 起始消息 ID
        - limit: 消息数量限制（默认 100）

        返回值：
        - Sequence[ChatMessage]: 消息列表（按时间升序）

        注意事项：
        - 用于增量拉取消息（如 WebSocket 推送或轮询）
        - 只返回 after_message_id 之后的消息
        - 按 id 升序排列
        - 限制最大返回数量避免数据量过大
        """

        messages = db.scalars(
            select(ChatMessage)
            .where(
                and_(
                    ChatMessage.session_id == session_id,
                    ChatMessage.id > after_message_id,
                )
            )
            .order_by(ChatMessage.id.asc())
            .limit(limit)
        ).all()

        logger.debug(
            "获取会话增量消息：session_id={}, after_id={}, count={}",
            session_id,
            after_message_id,
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
    def get_message_by_id(db: Session, message_id: int) -> ChatMessage | None:
        """根据 ID 获取消息。

        参数说明：
        - db: 数据库会话
        - message_id: 消息 ID

        返回值：
        - ChatMessage | None: 消息对象或 None（不存在）

        注意事项：
        - 不进行权限检查（由调用方确保）
        - 可以查询任意消息
        """

        message = db.get(ChatMessage, message_id)
        return message

    @staticmethod
    async def get_message_by_id_async(
        db: AsyncSession, message_id: int
    ) -> ChatMessage | None:
        """根据 ID 获取消息（异步版）。"""
        return await db.get(ChatMessage, message_id)

    @staticmethod
    def get_user_session_messages(
        db: Session,
        session_id: int,
        user_id: int,
        page: int = 1,
        size: int = 20,
    ) -> tuple[Sequence[ChatMessage], int]:
        """获取用户在某个会话中的消息列表（带权限检查）。

        参数说明：
        - db: 数据库会话
        - session_id: 会话 ID
        - user_id: 用户 ID
        - page: 页码（从 1 开始）
        - size: 每页数量

        返回值：
        - tuple: (消息列表, 总数量)

        注意事项：
        - 检查会话是否属于该用户
        - 如果会话不属于该用户，返回空列表
        - 普通用户只能查看自己的会话消息
        - 管理员需要使用 get_session_messages 方法
        """

        # 先检查会话是否属于该用户
        # 通过 ChatMessage 的 session_id 间接检查
        # 注意：这里假设 session_id 的 user_id 已经正确设置

        stmt = select(ChatMessage).where(
            and_(ChatMessage.session_id == session_id, ChatMessage.user_id == user_id)
        )

        # 查询总数
        count_stmt = select(func.count(ChatMessage.id)).where(
            and_(ChatMessage.session_id == session_id, ChatMessage.user_id == user_id)
        )

        total = db.scalar(count_stmt) or 0

        # 分页查询
        stmt = stmt.order_by(ChatMessage.id.asc()).offset((page - 1) * size).limit(size)

        messages = db.scalars(stmt).all()

        logger.debug(
            "查询用户会话消息：session_id={}, user_id={}, total={}, page={}, size={}",
            session_id,
            user_id,
            total,
            page,
            size,
        )

        return messages, total

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
