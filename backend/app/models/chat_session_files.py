from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, BigInteger, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ChatSessionFile(Base):
    """会话-文件关联表（chat_session_files）。

    说明：
    - 实现会话与文件的多对多关系
    - 一个会话可以关联多个文件，一个文件也可以被多个会话使用
    - 支持用户构建个人知识库，并在多个会话中复用
    - 管理员上传的公共文件可以被多个用户的会话使用

    使用示例：
        ```python
        # 创建会话时关联文件
        session_file = ChatSessionFile(
            chat_session_id=1,
            file_id=10
        )
        db.add(session_file)
        db.commit()

        # 查询某个会话关联的所有文件
        session_files = db.query(ChatSessionFile).filter(
            ChatSessionFile.chat_session_id == 1
        ).all()

        # 查询某个文件被哪些会话使用
        files = db.query(ChatSessionFile).filter(
            ChatSessionFile.file_id == 10
        ).all()
        ```

    设计要点：
    - 复合唯一索引：(chat_session_id, file_id) 避免重复关联
    - 不建外键约束，保持学习项目灵活性
    - create_time 用于记录关联时间，便于分析知识库使用情况
    """

    __tablename__ = "chat_session_files"

    # 主键
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键ID"
    )

    # 关联字段
    chat_session_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True, comment="会话ID，关联chat_session.id"
    )

    file_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True, comment="文件ID，关联file_storage.id"
    )

    # 时间戳
    create_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=True,
        comment="关联时间",
    )

    # 表级约束
    __table_args__ = (
        UniqueConstraint("chat_session_id", "file_id", name="uk_session_file"),
        # 说明：
        # - 确保同一个会话不会重复关联同一个文件
        # - uk_session_file 是索引名称，便于维护
    )
