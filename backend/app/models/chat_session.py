from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, BigInteger, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ChatSession(Base):
    """聊天会话表（chat_session）。"""

    __tablename__ = "chat_session"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="用户ID")
    biz_type: Mapped[str] = mapped_column(String(50), nullable=False, comment="业务类型")
    title: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="会话标题")
    context_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="上下文ID")
    status: Mapped[int] = mapped_column(Integer, default=1, nullable=True, comment="会话状态，1-进行中，0-已结束")
    create_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=True
    )
    update_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )
