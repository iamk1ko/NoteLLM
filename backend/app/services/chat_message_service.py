from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.crud.chat_message_crud import ChatMessageCRUD
from app.crud.chat_session_crud import ChatSessionCRUD
from app.models import ChatMessage, User
from app.schemas.chat_message import ChatMessageCreate

logger = get_logger(__name__)


class ChatMessageService:
    """聊天消息业务服务层。

    说明：
    - 处理消息的创建与查询
    - 控制会话访问权限（普通用户只能访问自己的会话）
    - 预留 LangChain 生成 AI 回复的接口
    """

    def __init__(self, db: Session):
        self.db = db

    def send_message(
        self, user: User, session_id: int, payload: ChatMessageCreate
    ) -> ChatMessage | None:
        """发送消息。

        说明：
        - 普通用户只能在自己的会话中发送消息
        - 管理员可以在任何会话中发送消息
        - role 默认是 user，也可以由系统生成 assistant 消息
        """

        # 权限检查：用户是否有权访问会话
        if user.role == "admin":
            session = ChatSessionCRUD.get_session_by_id(self.db, session_id)
        else:
            # TODO: 这里可以优化为只查询会话是否存在，避免加载过多无用数据。
            #  此外，session_id 已经是唯一标识了，不需要再加 user_id 作为联合查询条件（可优化CRUD代码）。
            session = ChatSessionCRUD.get_user_session(self.db, session_id, user.id)

        if not session:
            logger.warning("发送消息失败：会话不存在或无权限 session_id={}", session_id)
            return None

        return ChatMessageCRUD.create_message(
            db=self.db,
            session_id=session_id,
            user_id=user.id,
            content=payload.content,
            role=payload.role, # TODO: RAG 对话系统，发送消息这里只可能是 user，assistant 消息由系统生成在后续业务中创建 message 对象。
            model_name=payload.model_name,
        )

    def get_message_history(
        self,
        user: User,
        session_id: int,
        page: int = 1,
        size: int = 20,
    ) -> tuple[Sequence[ChatMessage], int]:
        """获取消息历史（分页）。

        说明：
        - 普通用户只能查看自己的会话消息
        - 管理员可以查看任意会话消息
        """

        if user.role == "admin":
            return ChatMessageCRUD.get_session_messages(
                db=self.db, session_id=session_id, page=page, size=size
            )

        return ChatMessageCRUD.get_user_session_messages(
            db=self.db,
            session_id=session_id,
            user_id=user.id,
            page=page,
            size=size,
        )

    def generate_ai_response(self, session_id: int, user_message: str) -> str:
        """调用 LangChain 生成 AI 回复（预留接口）。

        说明：
        - 本方法只提供思路，不实现具体模型调用
        - 后续可接入 langchain-ollama 或 OpenAI

        示例流程（思路）：
        1. 获取会话最近 10 条消息作为上下文
        2. 获取会话关联的知识库文件（file_ids）
        3. 从向量库检索相关 chunk
        4. 构建 prompt，调用 LLM
        5. 返回 AI 回复文本
        """

        logger.info("生成 AI 回复（预留接口）：session_id={}", session_id)

        # TODO: 这里仅返回固定占位内容，后续接入 LangChain
        return "（AI 回复占位文本）"
