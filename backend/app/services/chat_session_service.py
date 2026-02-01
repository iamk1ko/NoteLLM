from app.core.logging import get_logger
from sqlalchemy.orm import Session

logger = get_logger(__name__)


class ChatSessionService:
    """聊天会话业务服务层。

    """

    def __init__(self, db: Session):
        self.db = db

    def create_chat_session(self, payload) -> None:
        """创建聊天会话。

        说明：
        - payload 包含创建聊天会话所需的数据
        """
        logger.info("创建聊天会话，payload={}", payload)

