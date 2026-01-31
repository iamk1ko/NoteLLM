from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class UserBase(BaseModel):
    """用户基础模型。

    说明：
    - 放置创建、更新都会用到的公共字段
    - 这里不含密码，避免在列表/详情里误返回
    """

    username: str = Field(..., min_length=3, max_length=20, description="用户名")
    name: str = Field(..., min_length=1, max_length=10, description="姓名")
    gender: int = Field(3, ge=1, le=3, description="性别：1男 2女 3保密")
    phone: str | None = Field(None, max_length=11, description="手机号")
    email: str | None = Field(None, max_length=50, description="邮箱")
    avatar_file_id: int | None = Field(None, description="头像文件ID")
    bio: str | None = Field(None, max_length=255, description="个人简介")


class UserCreate(UserBase):
    """用户创建模型。

    说明：
    - password 需要传入哈希后的字符串
    - 学习项目中可以先明文，后续接入加密再替换
    """

    password: str = Field(..., min_length=6, max_length=255, description="密码hash")


class UserUpdate(BaseModel):
    """用户更新模型。

    说明：
    - 全部字段可选，仅更新传入的部分
    - 如果不更新密码，不要传 password
    """

    username: str | None = Field(
        None, min_length=3, max_length=20, description="用户名"
    )
    password: str | None = Field(
        None, min_length=6, max_length=255, description="密码hash"
    )
    name: str | None = Field(None, min_length=1, max_length=10, description="姓名")
    gender: int | None = Field(None, ge=1, le=3, description="性别：1男 2女 3保密")
    phone: str | None = Field(None, max_length=11, description="手机号")
    email: str | None = Field(None, max_length=50, description="邮箱")
    avatar_file_id: int | None = Field(None, description="头像文件ID")
    bio: str | None = Field(None, max_length=255, description="个人简介")


class UserOut(UserBase):
    """用户输出模型。

    说明：
    - 返回给前端的字段
    - 不包含 password，避免泄露
    """

    id: int
    create_time: datetime | None
    update_time: datetime | None

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    """用户分页响应模型。

    说明：
    - 用于列表分页接口
    - items 为当前页数据，total 为总数量
    """

    items: list[UserOut]
    total: int
    page: int
    size: int


class SimpleResponse(BaseModel):
    """通用简单响应。

    说明：
    - 适用于删除等只关心结果的场景
    """

    success: bool = True
