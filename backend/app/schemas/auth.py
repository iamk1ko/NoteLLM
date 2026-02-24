from __future__ import annotations

from pydantic import BaseModel, Field


class RegisterIn(BaseModel):
    """注册请求模型。"""

    username: str = Field(..., min_length=1, max_length=20, description="用户名")
    password: str = Field(..., min_length=1, max_length=255, description="密码")
    name: str = Field(..., min_length=1, max_length=10, description="姓名")
    email: str | None = Field(None, max_length=50, description="邮箱")


class LoginIn(BaseModel):
    """登录请求模型。"""

    username_or_email: str = Field(
        ..., min_length=1, max_length=50, description="用户名或邮箱"
    )
    password: str = Field(..., min_length=1, max_length=255, description="密码")


class LogoutOut(BaseModel):
    """退出登录响应模型。"""

    success: bool = True
