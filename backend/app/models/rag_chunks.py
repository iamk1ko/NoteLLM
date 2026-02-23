from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class RagChunks(Base):
    """语义切片与向量表（rag_chunks）。"""

    __tablename__ = "rag_chunks"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键ID"
    )
    file_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="所属文件ID（file_storage.id）"
    )
    chunk_index: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="语义切片索引，从0开始"
    )
    chunk_text: Mapped[str] = mapped_column(
        Text, nullable=False, comment="切片文本内容"
    )
    chunk_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="切片token数量"
    )
    page_no: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="页码（PDF等）"
    )
    section: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="章节/标题"
    )
    embedding_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment="向量库中的embedding标识"
    )
    status: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False, comment="切片状态：1-有效，2-删除，3-失败"
    )
    create_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=True,
        comment="创建时间",
    )
    update_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True, comment="更新时间"
    )
