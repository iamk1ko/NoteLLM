from __future__ import annotations

from datetime import datetime
from typing import Sequence

from pydantic import BaseModel, Field


class ChatSessionBase(BaseModel):
    """聊天会话基础模型。

    说明：
    - 定义会话的公共字段
    - 不包含 id 和时间戳，用于创建和更新
    """

    title: str | None = Field(None, description="会话标题")
    biz_type: str = Field(
        "ai_chat", description="业务类型：ai_chat/pdf_qa/customer_service等"
    )
    context_id: str | None = Field(None, description="外部上下文ID，如PDF文档ID")
    status: int = Field(1, ge=0, le=1, description="会话状态：1-正常，0-删除")


class ChatSessionCreate(ChatSessionBase):
    """聊天会话创建模型。

    使用示例：
        ```python
        # 创建新的AI对话会话
        session = ChatSessionCreate(
            title="关于RAG的讨论",
            biz_type="ai_chat"
        )

        # 创建PDF问答会话
        pdf_session = ChatSessionCreate(
            title="学习文档问答",
            biz_type="pdf_qa",
            context_id="doc_123"
        )
        ```
    """

    pass


class ChatSessionUpdate(BaseModel):
    """聊天会话更新模型。

    说明：
    - 全部字段可选，仅更新传入的部分
    - 不允许修改 user_id 和 biz_type

    使用示例：
        ```python
        # 更新会话标题
        update = ChatSessionUpdate(title="新标题")

        # 结束会话
        end_session = ChatSessionUpdate(status=0)
        ```
    """

    title: str | None = Field(None, max_length=255, description="会话标题")
    status: int | None = Field(None, ge=0, le=1, description="会话状态：1-正常，0-删除")


class ChatSessionOut(ChatSessionBase):
    """聊天会话输出模型。

    说明：
    - 返回给前端的完整会话信息
    - 包含 id、user_id 和时间戳
    - 可扩展 file_count 等统计信息
    """

    id: int = Field(..., description="会话ID")
    user_id: int = Field(..., description="用户ID")
    create_time: datetime | None = Field(None, description="创建时间")
    update_time: datetime | None = Field(None, description="更新时间")

    # 可选：关联文件数量（需要在查询时计算）
    file_count: int | None = Field(None, description="关联的文件数量")

    model_config = {"from_attributes": True}


class ChatSessionListResponse(BaseModel):
    """聊天会话列表响应模型。

    说明：
    - 用于分页返回会话列表
    - items 为当前页的会话列表
    - total 为总会话数量
    - 支持按创建时间倒序排列（最新会话在前）

    使用示例：
        ```python
        # 分页查询用户的会话列表
        response = ChatSessionListResponse(
            items=sessions,
            total=20,
            page=1,
            size=10
        )
        ```
    """

    items: Sequence[ChatSessionOut] = Field(..., description="会话列表")
    total: int = Field(..., description="总会话数量")
    page: int = Field(..., description="当前页码")
    size: int = Field(..., description="每页数量")


class ChatSessionWithFiles(ChatSessionOut):
    """带文件信息的会话输出模型。

    说明：
    - 继承自 ChatSessionOut
    - 扩展文件相关信息
    - 用于会话详情接口，返回关联的文件列表
    """

    files: Sequence[int] = Field([], description="关联的文件ID列表")
    # 说明：返回文件ID列表，前端可以单独调用文件接口获取详细信息


class SessionSummaryRequest(BaseModel):
    focus_topics: list[str] | None = Field(None, description="Focus topics for summary")


class SessionSummaryResponse(BaseModel):
    summary_content: str
    created_at: datetime
