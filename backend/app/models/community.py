from __future__ import annotations

from datetime import datetime
from sqlalchemy import Boolean, DateTime, Integer, String, BigInteger, func, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base


class CommunityShare(Base):
    __tablename__ = "community_share"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="Share ID"
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="Publisher User ID"
    )

    # Source Content
    source_file_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="Source File ID"
    )
    source_session_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="Source Session ID"
    )

    # Metadata
    title: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Share Title"
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Share Description"
    )
    tags: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="Comma separated tags"
    )

    # Settings
    is_public_source: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="Allow downloading source file"
    )

    # Stats
    view_count: Mapped[int] = mapped_column(Integer, default=0, comment="View Count")
    like_count: Mapped[int] = mapped_column(Integer, default=0, comment="Like Count")
    fork_count: Mapped[int] = mapped_column(Integer, default=0, comment="Fork Count")

    create_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), comment="Create Time"
    )
    update_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), comment="Update Time"
    )


class CommunityLike(Base):
    __tablename__ = "community_like"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    share_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="Share ID"
    )
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="User ID")
    create_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
