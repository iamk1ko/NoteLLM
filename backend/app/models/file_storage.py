from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, BigInteger, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class FileStorage(Base):
    """文件存储表（file_storage）。"""

    __tablename__ = "file_storage"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="上传用户ID")
    filename: Mapped[str] = mapped_column(String(255), nullable=False, comment="原始文件名")
    bucket_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="存储桶名称")
    object_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="对象名称")
    content_type: Mapped[str] = mapped_column(String(100), nullable=False, comment="文件MIME类型")
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="文件大小，单位字节")
    etag: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="文件ETag (MD5哈希值)")
    status: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="文件状态：1-可用，2-已删除，3-禁用")
    chat_session_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="关联的聊天会话ID")
    upload_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=True
    )
    update_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )
