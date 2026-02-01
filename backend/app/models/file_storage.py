from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, BigInteger, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class FileStorage(Base):
    """文件存储表（file_storage）。

    说明：
    - 存储上传文件的元数据信息
    - 支持私有文件和公共文件，实现知识库共享
    - 文件内容实际存储在 MinIO 对象存储中

    使用示例：
        ```python
        # 上传私有文件（默认）
        private_file = FileStorage(
            user_id=1,
            filename="document.pdf",
            bucket_name="user-files",
            object_name="user1/document.pdf",
            content_type="application/pdf",
            file_size=1024000,
            is_public=False
        )

        # 上传公共文件（管理员操作）
        public_file = FileStorage(
            user_id=1,  # 管理员的用户ID
            filename="manual.pdf",
            bucket_name="public-files",
            object_name="manual.pdf",
            content_type="application/pdf",
            file_size=2048000,
            is_public=True
        )

        # 查询某个用户的文件（含公共文件）
        user_files = db.query(FileStorage).filter(
            or_(
                FileStorage.user_id == user_id,
                FileStorage.is_public == True
            )
        ).all()

        # 查询所有公共文件
        public_files = db.query(FileStorage).filter(
            FileStorage.is_public == True
        ).all()
        ```

    权限说明：
    - 私有文件（is_public=False）：仅上传者可以使用
    - 公共文件（is_public=True）：所有用户都可以在会话中使用
    - 文件与会话通过 chat_session_files 表多对多关联

    注意：
    - chat_session_id 字段保留，用于直接上传场景（如快速创建带文件的会话）
    - 优先推荐使用 chat_session_files 表进行多对多关联
    """

    __tablename__ = "file_storage"

    # 主键
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键ID"
    )

    # 用户信息
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="上传用户ID")

    # 文件基本信息
    filename: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="原始文件名"
    )
    bucket_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="存储桶名称"
    )
    object_name: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="对象名称"
    )
    content_type: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="文件MIME类型"
    )
    file_size: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="文件大小，单位字节"
    )
    etag: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="文件ETag (MD5哈希值）"
    )

    # 公开性字段（新增）
    is_public: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="是否为公共文件：True-公共，False-私有",
    )

    # 状态字段
    status: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False, comment="文件状态：1-可用，2-已删除，3-禁用"
    )

    # 会话关联（保留用于快速创建场景）
    chat_session_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, comment="关联的聊天会话ID（可选，用于快速创建场景）"
    )

    # 时间戳
    upload_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=True,
        comment="上传时间",
    )
    update_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True, comment="更新时间"
    )
