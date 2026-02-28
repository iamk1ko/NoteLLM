from __future__ import annotations

from datetime import datetime
from typing import Sequence

from pydantic import BaseModel, Field

from app.core.settings import get_settings


class ChatMessageBase(BaseModel):
    """聊天消息基础模型。

    说明：
    - 定义消息的公共字段
    - 不包含 id 和时间戳，用于创建和更新
    """

    content: str = Field(..., description="消息内容")
    role: str = Field(default="user", description="消息角色：user/assistant/system/tool")
    model_name: str | None = Field(default=get_settings().LLM_MODEL, description="使用的模型名称")


class ChatMessageCreate(ChatMessageBase):
    """聊天消息创建模型。

    使用示例：
        ```python
        # 用户发送消息
        user_message = ChatMessageCreate(
            content="你好，请介绍一下RAG",
            role="user"
        )

        # AI回复消息（系统生成）
        ai_message = ChatMessageCreate(
            content="RAG是...",
            role="assistant",
            model_name="qwen3:0.6b"
        )
        ```
    """

    pass


class ChatMessageOut(BaseModel):
    """聊天消息输出模型。

    说明：
    - 返回给前端的完整消息信息
    - 包含 id 和时间戳
    - 不包含敏感信息
    """

    id: int = Field(..., description="消息ID")
    session_id: int = Field(..., description="会话ID")
    user_id: int = Field(..., description="用户ID")
    role: str = Field(..., description="消息角色：user/assistant/system/tool")
    content: str = Field(..., description="消息内容")
    model_name: str | None = Field(default=get_settings().LLM_MODEL, description="使用的模型名称")
    token_count: int | None = Field(None, description="消息的Token数量")
    create_time: datetime | None = Field(None, description="创建时间")

    model_config = {"from_attributes": True}


class ChatMessageListResponse(BaseModel):
    """聊天消息列表响应模型。

    说明：
    - 用于分页返回消息列表
    - items 为当前页的消息列表
    - total 为总消息数量
    - 支持按时间倒序排列（最新消息在前）

    使用示例：
        ```python
        # 分页查询消息
        response = ChatMessageListResponse(
            items=messages,
            total=100,
            page=1,
            size=10
        )
        ```
    """

    items: Sequence[ChatMessageOut] = Field(..., description="消息列表")
    total: int = Field(..., description="总消息数量")
    page: int = Field(..., description="当前页码")
    size: int = Field(..., description="每页数量")


class ChatMessageIn(BaseModel):
    """聊天消息输入模型（用于API接口）。

    说明：
    - 用于接收前端发送的消息
    - 简化字段，仅包含必要信息
    """

    content: str = Field(..., description="消息内容", min_length=1)
