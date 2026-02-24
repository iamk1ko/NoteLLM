from __future__ import annotations

from typing import Sequence
from sqlalchemy import select, func, desc, and_, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.community import CommunityShare, CommunityLike
from app.core.logging import get_logger

logger = get_logger(__name__)


class CommunityCRUD:
    @staticmethod
    async def create_share(
        db: AsyncSession,
        user_id: int,
        source_file_id: int,
        source_session_id: int,
        title: str,
        description: str | None = None,
        tags: str | None = None,
        is_public_source: bool = False,
    ) -> CommunityShare:
        share = CommunityShare(
            user_id=user_id,
            source_file_id=source_file_id,
            source_session_id=source_session_id,
            title=title,
            description=description,
            tags=tags,
            is_public_source=is_public_source,
        )
        db.add(share)
        await db.commit()
        await db.refresh(share)
        return share

    @staticmethod
    async def get_shares(
        db: AsyncSession,
        page: int = 1,
        size: int = 10,
        sort_by: str = "latest",  # latest, popular
        tag_filter: str | None = None,
    ) -> tuple[Sequence[CommunityShare], int]:
        stmt = select(CommunityShare)

        if tag_filter:
            stmt = stmt.where(CommunityShare.tags.contains(tag_filter))

        # Count total before pagination
        count_stmt = select(func.count(CommunityShare.id))
        if tag_filter:
            count_stmt = count_stmt.where(CommunityShare.tags.contains(tag_filter))

        total = await db.scalar(count_stmt) or 0

        # Sorting
        if sort_by == "popular":
            stmt = stmt.order_by(
                desc(CommunityShare.like_count), desc(CommunityShare.view_count)
            )
        else:
            stmt = stmt.order_by(desc(CommunityShare.create_time))

        stmt = stmt.offset((page - 1) * size).limit(size)

        result = await db.scalars(stmt)
        return result.all(), total

    @staticmethod
    async def get_share_by_id(db: AsyncSession, share_id: int) -> CommunityShare | None:
        return await db.get(CommunityShare, share_id)

    @staticmethod
    async def increment_view_count(db: AsyncSession, share_id: int):
        stmt = (
            update(CommunityShare)
            .where(CommunityShare.id == share_id)
            .values(view_count=CommunityShare.view_count + 1)
        )
        await db.execute(stmt)
        await db.commit()

    @staticmethod
    async def increment_fork_count(db: AsyncSession, share_id: int):
        stmt = (
            update(CommunityShare)
            .where(CommunityShare.id == share_id)
            .values(fork_count=CommunityShare.fork_count + 1)
        )
        await db.execute(stmt)
        await db.commit()

    # Like Logic
    @staticmethod
    async def get_like(
        db: AsyncSession, share_id: int, user_id: int
    ) -> CommunityLike | None:
        stmt = select(CommunityLike).where(
            and_(CommunityLike.share_id == share_id, CommunityLike.user_id == user_id)
        )
        return await db.scalar(stmt)

    @staticmethod
    async def like_share(db: AsyncSession, share_id: int, user_id: int) -> bool:
        # Check if already liked
        existing = await CommunityCRUD.get_like(db, share_id, user_id)
        if existing:
            return False

        # Add like record
        like = CommunityLike(share_id=share_id, user_id=user_id)
        db.add(like)

        # Increment count
        stmt = (
            update(CommunityShare)
            .where(CommunityShare.id == share_id)
            .values(like_count=CommunityShare.like_count + 1)
        )
        await db.execute(stmt)

        await db.commit()
        return True

    @staticmethod
    async def unlike_share(db: AsyncSession, share_id: int, user_id: int) -> bool:
        # Check if exists
        existing = await CommunityCRUD.get_like(db, share_id, user_id)
        if not existing:
            return False

        # Delete like record
        await db.delete(existing)

        # Decrement count
        stmt = (
            update(CommunityShare)
            .where(CommunityShare.id == share_id)
            .values(like_count=CommunityShare.like_count - 1)
        )
        await db.execute(stmt)

        await db.commit()
        return True
