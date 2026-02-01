from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import User


async def get_current_user_optional(request: Request) -> User | None:
    """获取当前登录用户（可选）。

    说明：
    - 从请求中解析 JWT Token
    - 如果未登录或 Token 无效，返回 None
    - 用于不需要强制登录的接口

    使用示例：
        ```python
        @router.get("/public-data")
        def get_public_data(current_user: User | None = Depends(get_current_user_optional)):
            if current_user:
                # 已登录用户可以看到更多信息
                return {"data": "public + private"}
            else:
                # 未登录用户只能看到公开信息
                return {"data": "public only"}
        ```

    注意事项：
    - 当前实现为占位符，需要后续实现具体的 JWT 解析逻辑
    - 生产环境中应实现：
      1. 从请求头或 Cookie 中获取 Token
      2. 验证 Token 签名和过期时间
      3. 从 Token 中解析用户 ID
      4. 从数据库加载用户信息
    """

    # TODO: 实现 JWT Token 解析逻辑
    # 占位符实现：从请求头或 Cookie 中获取用户信息
    token = request.headers.get("Authorization")
    if not token:
        return None

    # 提取 Bearer Token
    if token.startswith("Bearer "):
        token = token[7:]

    # TODO: 验证 Token 并解析用户 ID
    # 示例：
    # try:
    #     payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    #     user_id = payload.get("user_id")
    #     db = request.state.db  # 需要确保数据库连接可用
    #     user = db.get(User, user_id)
    #     return user
    # except JWTError:
    #     return None

    # 临时占位符：直接返回 None（表示未登录）
    return None


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

    # if current_user is None:
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="未提供认证信息或认证信息无效",
    #         headers={"WWW-Authenticate": "Bearer"},
    #     )

    # TODO: 目前模拟一个用户出来，后续集成用户系统后删除此行
    current_user = User(id=1, username="kiko", role="admin")

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
