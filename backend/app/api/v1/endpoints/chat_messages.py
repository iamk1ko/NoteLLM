from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.dependencies import get_current_user
from app.schemas.chat_message import (
    ChatMessageCreate,
    ChatMessageListResponse,
    ChatMessageOut,
)
from app.schemas.response import ApiResponse
from app.services.chat_message_service import ChatMessageService
from app.models import User

router = APIRouter(tags=["chat_messages"])


@router.post(
    "/sessions/{session_id}/messages",
    response_model=ApiResponse[ChatMessageOut],
)
def send_message(
        session_id: int,
        payload: ChatMessageCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
) -> ApiResponse[ChatMessageOut]:
    """发送消息。

    说明：
    - 普通用户只能在自己的会话中发送消息
    - 管理员可以在任何会话中发送消息
    """

    message = ChatMessageService(db).send_message(current_user, session_id, payload)

    if not message:
        # TODO: 后期可以服务降级处理，比如返回一个默认回复
        raise HTTPException(status_code=404, detail="会话不存在或无权限")

    return ApiResponse.ok(ChatMessageOut.model_validate(message))


@router.get(
    "/sessions/{session_id}/messages",
    response_model=ApiResponse[ChatMessageListResponse],
)
def get_message_history(
        session_id: int,
        page: int = Query(1, ge=1, description="页码，从 1 开始"),
        size: int = Query(20, ge=1, le=200, description="每页数量"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
) -> ApiResponse[ChatMessageListResponse]:
    """查询消息历史（分页）。"""

    items, total = ChatMessageService(db).get_message_history(
        current_user, session_id, page=page, size=size
    )
    payload = ChatMessageListResponse(
        items=[ChatMessageOut.model_validate(item) for item in items],
        total=total,
        page=page,
        size=size,
    )
    return ApiResponse.ok(payload)
