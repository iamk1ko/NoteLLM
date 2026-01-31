from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, BigInteger, String, Text, DECIMAL, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ChatContext(Base):
    """聊天上下文引用表（chat_context）。"""

    __tablename__ = "chat_context"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reference_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reference_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    similarity: Mapped[float | None] = mapped_column(DECIMAL(6, 4), nullable=True)
    create_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=True
    )
