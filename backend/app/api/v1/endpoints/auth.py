from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import RedisKey
from app.core.logging import get_logger
from app.core.redis_client import get_redis_client
from app.core.settings import get_settings
from app.core.db import get_async_db
from app.crud import UserCRUD
from app.models import User, UserStatus, UserRole
from app.schemas.auth import RegisterIn, LoginIn, LogoutOut
from app.schemas.response import ApiResponse
from app.schemas.users import UserOut

import uuid

router = APIRouter(tags=["auth"])
logger = get_logger(__name__)


@router.post("/auth/register", response_model=ApiResponse[UserOut])
async def register(
    payload: RegisterIn,
    db: AsyncSession = Depends(get_async_db),
) -> ApiResponse[UserOut]:
    """用户注册。

    说明：
    - 本地学习场景，密码明文存储
    - 用户名与邮箱唯一性需校验
    """

    existing_user = await UserCRUD.get_user_by_username_async(db, payload.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="用户名已存在")

    if payload.email:
        existing_email = await UserCRUD.get_user_by_email_async(db, payload.email)
        if existing_email:
            raise HTTPException(status_code=400, detail="邮箱已存在")

    user = User(
        username=payload.username,
        password=payload.password,
        name=payload.name,
        email=payload.email,
        role=UserRole.USER.value,
        status=UserStatus.ACTIVE.value,
    )
    user = await UserCRUD.create_user_async(db, user)
    logger.info("用户注册成功：user_id={}, username={}", user.id, user.username)
    return ApiResponse.ok(UserOut.model_validate(user))


@router.post("/auth/login", response_model=ApiResponse[UserOut])
async def login(
    payload: LoginIn,
    response: Response,
    db: AsyncSession = Depends(get_async_db),
) -> ApiResponse[UserOut]:
    """用户登录。

    说明：
    - 用户名或邮箱登录
    - 校验密码是否一致
    - 登录成功后设置 session_id Cookie
    """

    user = await UserCRUD.get_user_by_username_async(db, payload.username_or_email)
    if user is None:
        user = await UserCRUD.get_user_by_email_async(db, payload.username_or_email)
    if user is None:
        raise HTTPException(status_code=400, detail="用户名或密码错误")

    if user.password != payload.password:
        raise HTTPException(status_code=400, detail="用户名或密码错误")

    if user.status != UserStatus.ACTIVE.value:
        raise HTTPException(status_code=403, detail="用户已被禁用")

    session_id = uuid.uuid4().hex
    settings = get_settings()
    redis_client = get_redis_client()
    await redis_client.set(
        RedisKey.USER_SESSION.format(session_id),
        str(user.id),
        ex=settings.AUTH_SESSION_TTL_SECONDS,
    )

    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        samesite="lax",
        max_age=settings.AUTH_SESSION_TTL_SECONDS,
    )

    logger.info("用户登录成功：user_id={}, username={}", user.id, user.username)
    return ApiResponse.ok(UserOut.model_validate(user))


@router.post("/auth/logout", response_model=ApiResponse[LogoutOut])
async def logout(request: Request, response: Response) -> ApiResponse[LogoutOut]:
    """退出登录。

    说明：
    - 清理 Redis session
    - 清除 Cookie
    """

    session_id = request.cookies.get("session_id")
    if session_id:
        redis_client = get_redis_client()
        await redis_client.delete(RedisKey.USER_SESSION.format(session_id))

    response.delete_cookie("session_id")
    logger.info("用户退出登录")
    return ApiResponse.ok(LogoutOut(success=True))
