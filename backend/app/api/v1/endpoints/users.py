from __future__ import annotations

from typing import Sequence

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.services.users_service import UserService
from app.models.users import User
from app.schemas.users import (
    UserOut,
    UserCreate,
    UserUpdate,
    UserListResponse,
    SimpleResponse,
)
from app.schemas.response import ApiResponse

router = APIRouter(tags=["users"])


@router.get("/users", response_model=ApiResponse[Sequence[UserOut]])
def list_users(db: Session = Depends(get_db)) -> Sequence[User]:
    """获取所有用户列表（不分页）。

    说明：
    - 适合数据量很小的场景
    - 如果数据量较大，请使用分页接口 /users/page
    """

    items = UserService(db).list_users()
    return ApiResponse.ok([UserOut.model_validate(item) for item in items])


@router.get("/users/page", response_model=ApiResponse[UserListResponse])
def list_users_page(
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    size: int = Query(10, ge=1, le=100, description="每页数量"),
    keyword: str | None = Query(None, description="模糊搜索关键词"),
    db: Session = Depends(get_db),
) -> UserListResponse:
    """分页查询用户列表。

    说明：
    - keyword 会匹配 username/name/phone/email
    - 返回 items 与 total，便于前端分页
    """

    items, total = UserService(db).list_users_page(
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
def get_user(user_id: int, db: Session = Depends(get_db)) -> User:
    """获取用户详情。"""

    user = UserService(db).get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return ApiResponse.ok(UserOut.model_validate(user))


@router.post("/users", response_model=ApiResponse[UserOut])
def create_user(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    """创建用户。"""

    user = UserService(db).create_user(payload)
    return ApiResponse.ok(UserOut.model_validate(user))


@router.put("/users/{user_id}", response_model=ApiResponse[UserOut])
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
) -> User:
    """更新用户。"""

    user = UserService(db).update_user(user_id, payload)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return ApiResponse.ok(UserOut.model_validate(user))


@router.delete("/users/{user_id}", response_model=ApiResponse[SimpleResponse])
def delete_user(
    user_id: int, db: Session = Depends(get_db)
) -> ApiResponse[SimpleResponse]:
    """删除用户。"""

    ok = UserService(db).delete_user(user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="用户不存在")
    return ApiResponse.ok(SimpleResponse(success=True))
