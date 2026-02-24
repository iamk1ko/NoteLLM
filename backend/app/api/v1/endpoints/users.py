from __future__ import annotations

from typing import Sequence

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_async_db
from app.services.users_service import UserService
from app.schemas.users import (
    UserOut,
    UserCreate,
    UserUpdate,
    UserListResponse,
    SimpleResponse,
)
from app.dependencies import get_current_user
from app.models import User
from app.schemas.response import ApiResponse

router = APIRouter(tags=["users"])


@router.get("/users", response_model=ApiResponse[Sequence[UserOut]])
async def list_users(
    db: AsyncSession = Depends(get_async_db),
) -> ApiResponse[list[UserOut]]:
    """获取所有用户列表（不分页）。

    说明：
    - 适合数据量很小的场景
    - 如果数据量较大，请使用分页接口 /users/page
    """

    items = await UserService(db).list_users()
    return ApiResponse.ok([UserOut.model_validate(item) for item in items])


@router.get("/users/page", response_model=ApiResponse[UserListResponse])
async def list_users_page(
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    size: int = Query(10, ge=1, le=100, description="每页数量"),
    keyword: str | None = Query(None, description="模糊搜索关键词"),
    db: AsyncSession = Depends(get_async_db),
) -> ApiResponse[UserListResponse]:
    """分页查询用户列表。

    说明：
    - keyword 会匹配 username/name/phone/email
    - 返回 items 与 total，便于前端分页
    """

    items, total = await UserService(db).list_users_page(
        page=page, size=size, keyword=keyword
    )
    payload = UserListResponse(
        items=[UserOut.model_validate(item) for item in items],
        total=total,
        page=page,
        size=size,
    )
    return ApiResponse.ok(payload)


@router.get("/users/{user_id}", response_model=ApiResponse[UserOut])
async def get_user(
    user_id: int, db: AsyncSession = Depends(get_async_db)
) -> ApiResponse[UserOut]:
    """获取用户详情。"""

    user = await UserService(db).get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return ApiResponse.ok(UserOut.model_validate(user))


@router.get("/users/me", response_model=ApiResponse[UserOut])
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
) -> ApiResponse[UserOut]:
    """获取当前登录用户信息。"""

    return ApiResponse.ok(UserOut.model_validate(current_user))


@router.post("/users", response_model=ApiResponse[UserOut])
async def create_user(
    payload: UserCreate, db: AsyncSession = Depends(get_async_db)
) -> ApiResponse[UserOut]:
    """创建用户。"""

    user = await UserService(db).create_user(payload)
    return ApiResponse.ok(UserOut.model_validate(user))


@router.put("/users/{user_id}", response_model=ApiResponse[UserOut])
async def update_user(
    user_id: int,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_async_db),
) -> ApiResponse[UserOut]:
    """更新用户。"""

    user = await UserService(db).update_user(user_id, payload)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return ApiResponse.ok(UserOut.model_validate(user))


@router.delete("/users/{user_id}", response_model=ApiResponse[SimpleResponse])
async def delete_user(
    user_id: int, db: AsyncSession = Depends(get_async_db)
) -> ApiResponse[SimpleResponse]:
    """删除用户。"""

    ok = await UserService(db).delete_user(user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="用户不存在")
    return ApiResponse.ok(SimpleResponse(success=True))
