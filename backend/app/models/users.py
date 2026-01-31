from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Users(Base):
    """用户表（users）。

    说明：
    - 用于账号、身份信息
    - 不在此处建立复杂外键，便于学习与迁移
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(10), nullable=False)
    gender: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(11), unique=True, nullable=True)
    email: Mapped[str | None] = mapped_column(String(50), nullable=True)
    avatar_file_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bio: Mapped[str | None] = mapped_column(
        String(255), default="这个人很懒,什么都没写...", nullable=True
    )
    create_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=True
    )
    update_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )
