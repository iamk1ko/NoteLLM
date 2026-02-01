from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, BigInteger, Text, Enum, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ChatMessage(Base):
    """聊天消息表（chat_message）。"""

    __tablename__ = "chat_message"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键ID"
    )
    session_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="会话ID"
    )
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="用户ID")
    role: Mapped[str] = mapped_column(
        Enum("user", "assistant", "system", "tool", name="chat_role"),
        nullable=False,
        comment="消息角色",
    )
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="消息内容")
    model_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="使用的模型名称"
    )
    token_count: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="消息的Token数量"
    )
    create_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=True
    )
