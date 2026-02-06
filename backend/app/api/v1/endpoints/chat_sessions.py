from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.dependencies.auth import get_current_user
from app.core.logging import get_logger
from app.models import User
from app.schemas.chat_session import (
    ChatSessionCreate,
    ChatSessionListResponse,
    ChatSessionOut,
    ChatSessionWithFiles,
)
from app.schemas.response import ApiResponse
from app.services.chat_session_service import ChatSessionService

logger = get_logger(__name__)

router = APIRouter(tags=["chat_sessions"])


class SessionFileBindIn(BaseModel):
    """会话-文件关联请求模型。

    说明：
    - file_ids 为需要关联/解绑的文件ID列表
    """

    file_ids: list[int] = Field(..., description="文件ID列表", min_length=1)


@router.post("/sessions", response_model=ApiResponse[ChatSessionOut])
def create_session(
    payload: ChatSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[ChatSessionOut]:
    """创建会话。

    说明：
    - 普通用户只能创建自己的会话
    - 管理员也可创建会话（作为测试使用）
    """

    session = ChatSessionService(db).create_session(current_user, payload)
    return ApiResponse.ok(ChatSessionOut.model_validate(session))


@router.get("/sessions", response_model=ApiResponse[ChatSessionListResponse])
def list_sessions(
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    size: int = Query(10, ge=1, le=100, description="每页数量"),
    biz_type: str | None = Query(None, description="业务类型过滤"),
    user_id: int | None = Query(None, description="管理员可指定用户ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[ChatSessionListResponse]:
    """查询会话列表（分页）。

    说明：
    - 普通用户只能查看自己的会话
    - 管理员可查看全部会话，或按 user_id 过滤
    """

    items, total = ChatSessionService(db).list_sessions(
        current_user, page=page, size=size, biz_type=biz_type, query_user_id=user_id
    )
    payload = ChatSessionListResponse(
        items=[ChatSessionOut.model_validate(item) for item in items],
        total=total,
        page=page,
        size=size,
    )
    return ApiResponse.ok(payload)


@router.get("/sessions/{session_id}", response_model=ApiResponse[ChatSessionWithFiles])
def get_session_detail(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[ChatSessionWithFiles]:
    """获取会话详情。

    说明：
    - 返回会话基本信息 + 关联文件ID列表
    """

    service = ChatSessionService(db)
    session = service.get_session_detail(current_user, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在或无权限")

    file_ids = ChatSessionService(db).get_session_files_ids(session_id)
    payload = ChatSessionWithFiles(
        **ChatSessionOut.model_validate(session).model_dump(),
        files=file_ids,
    )
    return ApiResponse.ok(payload)


@router.delete("/sessions/{session_id}", response_model=ApiResponse[dict])
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[dict]:
    """删除会话。

    说明：
    - 仅删除会话记录
    - 不处理消息和文件关联（可在 Service 内扩展）
    """

    ok = ChatSessionService(db).delete_session(current_user, session_id)
    if not ok:
        raise HTTPException(status_code=404, detail="会话不存在或无权限")
    return ApiResponse.ok({"success": True})


@router.post("/sessions/{session_id}/files", response_model=ApiResponse[dict])
def attach_files(
    session_id: int,
    payload: SessionFileBindIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[dict]:
    """关联文件到会话。

    说明：
    - 普通用户只能关联自己或公共文件
    - 管理员可关联任意文件
    """

    count = ChatSessionService(db).attach_files(
        current_user, session_id, payload.file_ids
    )
    return ApiResponse.ok({"success": True, "count": count})


@router.delete("/sessions/{session_id}/files", response_model=ApiResponse[dict])
def detach_files(
    session_id: int,
    payload: SessionFileBindIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[dict]:
    """取消文件与会话关联。"""

    count = ChatSessionService(db).detach_files(
        current_user, session_id, payload.file_ids
    )
    return ApiResponse.ok({"success": True, "count": count})
