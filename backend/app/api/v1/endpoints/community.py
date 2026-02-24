from __future__ import annotations
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, update, delete, and_
from app.core.db import get_async_db
from app.dependencies import get_current_user
from app.models import User
from app.models.community import CommunityShare, CommunityLike
from app.schemas.community import (
    PublishShareRequest,
    SharePublishResponse,
    CommunityListResponse,
    CommunityItem,
    LikeShareRequest,
    LikeShareResponse,
    ForkShareResponse,
)
from app.schemas.response import ApiResponse

router = APIRouter(tags=["community"])


@router.post("/shares", response_model=ApiResponse[SharePublishResponse])
async def publish_share(
    request: PublishShareRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """发布分享"""
    share = CommunityShare(
        user_id=current_user.id,
        source_file_id=request.source_file_id,
        source_session_id=request.session_id,
        title=request.title,
        description=request.description,
        tags=",".join(request.tags) if request.tags else None,
        is_public_source=request.is_public_source,
    )
    db.add(share)
    await db.commit()
    await db.refresh(share)

    return ApiResponse.ok(
        SharePublishResponse(share_id=share.id, publish_time=share.create_time)
    )


@router.get("/shares", response_model=ApiResponse[CommunityListResponse])
async def list_shares(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    sort: str = Query("latest"),
    tag: str = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """获取社区列表"""
    # Build query
    stmt = select(CommunityShare, User.name).join(
        User, CommunityShare.user_id == User.id
    )

    if tag:
        stmt = stmt.where(CommunityShare.tags.like(f"%{tag}%"))

    if sort == "popular":
        stmt = stmt.order_by(desc(CommunityShare.view_count))
    else:
        stmt = stmt.order_by(desc(CommunityShare.create_time))

    # Pagination
    total_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(total_stmt)

    stmt = stmt.offset((page - 1) * size).limit(size)
    result = await db.execute(stmt)
    rows = result.all()

    # Check likes
    share_ids = [row[0].id for row in rows]
    liked_map = {}
    if share_ids:
        like_stmt = select(CommunityLike.share_id).where(
            and_(
                CommunityLike.share_id.in_(share_ids),
                CommunityLike.user_id == current_user.id,
            )
        )
        liked_result = await db.execute(like_stmt)
        liked_shares = {r[0] for r in liked_result.all()}
        for sid in share_ids:
            liked_map[sid] = sid in liked_shares

    items = []
    for share, user_name in rows:
        items.append(
            CommunityItem(
                id=share.id,
                title=share.title,
                description=share.description,
                tags=share.tags.split(",") if share.tags else [],
                user_id=share.user_id,
                user_name=user_name,
                view_count=share.view_count,
                like_count=share.like_count,
                fork_count=share.fork_count,
                create_time=share.create_time,
                is_liked=liked_map.get(share.id, False),
            )
        )

    return ApiResponse.ok(
        CommunityListResponse(items=items, total=total or 0, page=page, size=size)
    )


@router.post("/shares/{share_id}/like", response_model=ApiResponse[LikeShareResponse])
async def like_share(
    share_id: int,
    request: LikeShareRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """点赞/取消点赞"""
    # Check if share exists
    share = await db.get(CommunityShare, share_id)
    if not share:
        raise HTTPException(status_code=404, detail="分享不存在")

    # Check existing like
    stmt = select(CommunityLike).where(
        and_(
            CommunityLike.share_id == share_id, CommunityLike.user_id == current_user.id
        )
    )
    existing_like = await db.scalar(stmt)

    if request.action == "like":
        if not existing_like:
            new_like = CommunityLike(share_id=share_id, user_id=current_user.id)
            db.add(new_like)
            share.like_count += 1
    else:  # unlike
        if existing_like:
            await db.delete(existing_like)
            share.like_count = max(0, share.like_count - 1)

    await db.commit()
    await db.refresh(share)

    return ApiResponse.ok(LikeShareResponse(success=True, like_count=share.like_count))


@router.post("/shares/{share_id}/fork", response_model=ApiResponse[ForkShareResponse])
async def fork_share(
    share_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """转存/Fork (Mock实现)"""
    share = await db.get(CommunityShare, share_id)
    if not share:
        raise HTTPException(status_code=404, detail="分享不存在")

    # Increment fork count
    share.fork_count += 1
    await db.commit()

    # In a real implementation, we would copy the file and session here.
    # For now, we return mock IDs to simulate success.
    return ApiResponse.ok(
        ForkShareResponse(
            new_file_id=share.source_file_id,  # Reuse for now
            new_session_id=share.source_session_id,  # Reuse for now
        )
    )
