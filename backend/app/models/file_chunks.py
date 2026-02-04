from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, BigInteger, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column
from enum import IntEnum

from app.core.db import Base

class FileChunksStatus(IntEnum):
    """文件状态枚举：0-上传中，1-已上传，2-已合并，3-失败/删除"""

    UPLOADING = 0
    UPLOADED = 1
    EMERGED = 2
    FAILED = 3

class FileChunks(Base):
    """文件分片表（file_chunks）。

    说明：
    - 存储上传分片的元信息（不是 RAG 切片）
    - 用于断点续传与分片合并
    - RAG 切片表后续单独设计
    """

    __tablename__ = "file_chunks"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键ID"
    )
    file_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, comment="所属文件ID（合并成功后回填）"
    )
    file_md5: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="文件MD5，用于上传会话标识"
    )
    chunk_index: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="分片索引，从0开始"
    )
    chunk_size: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="分片大小（字节）"
    )
    etag: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="分片ETag/MD5"
    )
    bucket_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="临时桶名称"
    )
    object_name: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="分片对象名称"
    )
    status: Mapped[int] = mapped_column(
        Integer,
        default=FileChunksStatus.UPLOADING.value,
        nullable=False,
        comment="分片状态：0-上传中，1-已上传，2-已合并，3-失败",
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
