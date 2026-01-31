from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

# 重要：统一使用 app.* 作为导入前缀，避免同一模块被加载两次
from app.core.db import Base


class User(Base):
    """用户表（user）。

    说明：
    - id: 主键，自增
    - username: 用户名，唯一
    - email: 邮箱，唯一
    - created_at: 创建时间，默认当前时间
    """

    __tablename__ = "user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )
    email: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
