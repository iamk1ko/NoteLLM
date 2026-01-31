from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, BigInteger, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class FileChunks(Base):
    """文件切片表（file_chunks）。"""

    __tablename__ = "file_chunks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    file_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="所属文件ID")
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, comment="切片索引，从0开始")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="切片内容")
    embedding_id: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="向量存储ID")
    create_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=True
    )
