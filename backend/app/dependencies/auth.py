from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from app.core.constants import RedisKey
from app.core.logging import get_logger
from app.core.redis_client import get_redis_client
from app.crud import UserCRUD
from app.models import User

logger = get_logger(__name__)


async def get_current_user_optional(request: Request) -> User | None:
    """获取当前登录用户（可选）。

    说明：
    - 从 Cookie 中解析 session_id
    - 如果未登录或 session 无效，返回 None
    """

    session_id = request.cookies.get("session_id")
    if not session_id:
        return None

    redis_client = get_redis_client()
    user_id = await redis_client.get(RedisKey.USER_SESSION.format(session_id))
    if not user_id:
        return None

    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        return None

    db = request.state.db
    if db is None:
        return None

    user = await UserCRUD.get_user_by_id_async(db, user_id_int)
    if user is None:
        return None

    logger.debug("当前登录用户解析成功：user_id={}", user.id)
    return user


async def get_current_user(
    current_user: Annotated[User | None, Depends(get_current_user_optional)],
) -> User:
    """获取当前登录用户（必需）。

    说明：
    - 要求用户必须登录
    - 如果未登录，抛出 401 异常
    - 用于需要认证的接口

    使用示例：
        ```python
        @router.get("/user-profile")
        def get_profile(current_user: User = Depends(get_current_user)):
            return {
                "username": current_user.username,
                "email": current_user.email,
                "role": current_user.role
            }
        ```

    异常：
    - 401 Unauthorized: 未提供有效 Token
    - 403 Forbidden: 用户权限不足（配合 require_admin 使用）
    """

    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证信息或认证信息无效",
        )

    return current_user


def require_admin(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """要求管理员权限的依赖。

    说明：
    - 检查当前用户是否为管理员
    - 如果不是管理员，抛出 403 异常
    - 用于管理员专属的接口

    使用示例：
        ```python
        @router.post("/upload-public-file")
        def upload_public_file(
            file: UploadFile,
            current_user: User = Depends(require_admin)
        ):
            # 只有管理员可以上传公共文件
            # ... 上传逻辑 ...
            return {"message": "公共文件上传成功"}
        ```

    权限说明：
    - admin: 可以访问所有接口，包括管理接口
    - user: 只能访问自己的资源，不能访问管理接口

    异常：
    - 403 Forbidden: 用户不是管理员
    """

    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )

    return current_user


def require_ownership(
    current_user: Annotated[User, Depends(get_current_user)],
    owner_id: int | None = None,
    resource_user_id: int | None = None,
) -> bool:
    """检查资源所有权或管理员权限。

    说明：
    - 检查当前用户是否为资源所有者或管理员
    - 用于确保用户只能访问自己的资源
    - 管理员可以访问所有资源

    使用示例：
        ```python
        @router.delete("/sessions/{session_id}")
        def delete_session(
            session_id: int,
            current_user: User = Depends(get_current_user),
            db: Session = Depends(get_db)
        ):
            # 获取会话
            session = db.get(ChatSession, session_id)
            if not session:
                raise HTTPException(404, "会话不存在")

            # 检查所有权
            is_authorized = require_ownership(
                current_user=current_user,
                resource_user_id=session.user_id
            )
            if not is_authorized:
                raise HTTPException(403, "无权操作该资源")

            # ... 删除逻辑 ...
        ```

    参数说明：
    - current_user: 当前登录用户（从 get_current_user 依赖注入）
    - owner_id: 资源所有者 ID（可选，用于函数参数）
    - resource_user_id: 资源关联的用户 ID（可选，用于数据库查询结果）

    返回值：
    - True: 用户是资源所有者或管理员
    - False: 用户不是资源所有者也不是管理员

    注意事项：
    - 该函数不直接抛出异常，返回布尔值
    - 调用者需要根据返回值决定是否抛出异常
    - 提供两种方式指定资源所有者（参数或数据库查询结果）
    """

    # 如果是管理员，直接通过
    if current_user.role == "admin":
        return True

    # 检查资源所有者
    owner = owner_id or resource_user_id
    if owner is not None and current_user.id == owner:
        return True

    return False
