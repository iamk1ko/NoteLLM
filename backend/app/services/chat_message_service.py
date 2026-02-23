from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.crud import ChatMessageCRUD, ChatSessionCRUD
from app.models import ChatMessage, User
from app.schemas.chat_message import ChatMessageCreate

logger = get_logger(__name__)


class ChatMessageService:
    """聊天消息业务服务层（异步版）。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def send_message(
        self, user: User, session_id: int, payload: ChatMessageCreate
    ) -> ChatMessage | None:
        """发送消息。"""

        # 权限检查：用户是否有权访问会话
        if user.role == "admin":
            session = await ChatSessionCRUD.get_session_by_id_async(self.db, session_id)
        else:
            session = await ChatSessionCRUD.get_user_session_async(
                self.db, session_id, user.id
            )

        if not session:
            logger.warning("发送消息失败：会话不存在或无权限 session_id={}", session_id)
            return None

        return await ChatMessageCRUD.create_message_async(
            db=self.db,
            session_id=session_id,
            user_id=user.id,
            content=payload.content,
            role=payload.role,
            model_name=payload.model_name,
        )

    async def get_message_history(
        self,
        user: User,
        session_id: int,
        page: int = 1,
        size: int = 20,
    ) -> tuple[Sequence[ChatMessage], int]:
        """获取消息历史（分页）。"""

        if user.role == "admin":
            return await ChatMessageCRUD.get_session_messages_async(
                db=self.db, session_id=session_id, page=page, size=size
            )

        return await ChatMessageCRUD.get_user_session_messages_async(
            db=self.db,
            session_id=session_id,
            user_id=user.id,
            page=page,
            size=size,
        )

    async def generate_ai_response(self, session_id: int, user_message: str) -> str:
        """调用 LangChain 生成 AI 回复（预留接口）。"""

        logger.info("生成 AI 回复（预留接口）：session_id={}", session_id)
        return "（AI 回复占位文本）"
