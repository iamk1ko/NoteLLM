from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class User(Base):
    """用户表（users）。

    说明：
    - 用于账号、身份信息
    - 支持角色管理（user/admin），实现权限隔离
    - 不在此处建立复杂外键，便于学习与迁移

    使用示例：
        ```python
        # 创建普通用户
        user = User(
            username="zhangsan",
            password="hash_password",  # 实际应存储密码哈希
            name="张三",
            role="user"
        )

        # 创建管理员用户
        admin = User(
            username="admin",
            password="admin_hash",
            name="管理员",
            role="admin"
        )

        # 查询管理员
        admins = db.query(User).filter(User.role == "admin").all()

        # 权限检查
        if user.role == "admin":
            # 管理员可以访问所有资源
            pass
        else:
            # 普通用户只能访问自己的资源
            pass
        ```

    角色说明：
    - user: 普通用户，只能访问自己的聊天会话和私有文件
    - admin: 管理员，可以访问所有用户的会话，上传公共文件，管理系统资源
    """

    __tablename__ = "users"

    # 主键
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="用户ID"
    )

    # 基础信息
    username: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, comment="用户名"
    )
    password: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="密码（哈希值）"
    )
    name: Mapped[str] = mapped_column(String(10), nullable=False, comment="真实姓名")

    # 角色字段（新增）
    role: Mapped[str] = mapped_column(
        String(20),
        default="user",
        nullable=False,
        comment="用户角色：user-普通用户，admin-管理员",
    )

    # 个人信息
    gender: Mapped[int] = mapped_column(
        Integer, default=3, nullable=False, comment="性别：1-男，2-女，3-保密"
    )
    phone: Mapped[str | None] = mapped_column(
        String(11), unique=True, nullable=True, comment="手机号"
    )
    email: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="电子邮箱"
    )
    avatar_file_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="头像文件ID"
    )
    bio: Mapped[str | None] = mapped_column(
        String(255),
        default="这个人很懒,什么都没写...",
        nullable=True,
        comment="个人简介",
    )

    # 时间戳
    create_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=True,
        comment="创建时间",
    )
    update_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True, comment="更新时间"
    )
