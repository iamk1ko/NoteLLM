from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.core.logging import get_logger
from app.core.db import get_async_db

logger = get_logger(__name__)
from app.dependencies.auth import get_current_user
from app.schemas.chat_message import (
    ChatMessageCreate,
    ChatMessageListResponse,
    ChatMessageOut,
)
from app.schemas.response import ApiResponse
from app.services.chat_message_service import ChatMessageService
from app.models import User
from app.services.llm.service import LLMService
from app.services.memory.markdown_memory import MarkdownMemoryService
from app.services.memory.redis_memory import RedisChatMemory
from app.core.redis_client import get_redis_client
from app.core.minio_client import get_minio_client

router = APIRouter(tags=["chat_messages"])


async def get_redis_client_dep() -> Redis:
    """Redis 依赖注入"""
    return get_redis_client()


async def get_llm_service_dep() -> LLMService:
    """LLM 服务依赖注入"""
    from app.services.llm.service import LLMService
    from app.core.settings import get_settings

    settings = get_settings()
    if not settings.BLSC_API_KEY or not settings.BLSC_BASE_URL:
        raise HTTPException(status_code=500, detail="LLM not configured")

    return LLMService(
        api_key=settings.BLSC_API_KEY,
        base_url=settings.BLSC_BASE_URL,
        model=settings.LLM_MODEL,
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
    )


async def get_markdown_memory_dep() -> MarkdownMemoryService:
    """Markdown 记忆服务依赖注入"""
    return MarkdownMemoryService(get_minio_client())


def get_redis_memory_factory_dep(redis_client: Redis = Depends(get_redis_client_dep)):
    """Redis 记忆工厂函数依赖注入"""

    def create(session_id: int) -> RedisChatMemory:
        return RedisChatMemory(redis_client, session_id)

    return create


async def get_rag_service_factory_dep(request: Request):
    """RAG 服务工厂函数依赖注入"""
    from app.core.app_state import get_app_state
    from app.services.rag.service import RagService
    from app.services.vectorization.embedder import BgeM3Embedder
    from app.core.settings import get_settings
    from app.core.redis_client import get_redis_client

    async def create_rag_service(db: AsyncSession) -> RagService | None:
        try:
            settings = get_settings()
            redis_client = get_redis_client()

            app_state = get_app_state(request.app)
            infra = app_state.infra

            if infra is None or infra.milvus is None:
                logger.warning("Milvus 实例未初始化，跳过 RAG 检索")
                return None

            milvus = infra.milvus

            embedder = BgeM3Embedder(
                model_name=settings.EMBEDDING_MODEL_NAME,
                device=settings.EMBEDDING_DEVICE,
                use_fp16=False,
            )

            return RagService(
                db=db,
                redis_client=redis_client,
                vector_store=milvus,
                embedder=embedder,
                history_limit=settings.RAG_HISTORY_LIMIT,
                cache_ttl_seconds=settings.RAG_CACHE_TTL,
                alpha=settings.RAG_RANKER_ALPHA,
            )
        except Exception as e:
            logger.error("创建 RAG 服务失败: {}", e)
            return None

    return create_rag_service


def get_chat_service(
    db: AsyncSession = Depends(get_async_db),
    llm_service: LLMService = Depends(get_llm_service_dep),
    redis_memory_factory=Depends(get_redis_memory_factory_dep),
    markdown_memory: MarkdownMemoryService = Depends(get_markdown_memory_dep),
    rag_service_factory=Depends(get_rag_service_factory_dep),
) -> ChatMessageService:
    """ChatMessageService 工厂函数 - 注入所有依赖"""
    return ChatMessageService(
        db=db,
        llm_service=llm_service,
        redis_memory_factory=redis_memory_factory,
        markdown_memory=markdown_memory,
        rag_service_factory=rag_service_factory,
    )


@router.post(
    "/sessions/{session_id}/messages",
    response_model=ApiResponse[ChatMessageOut],
)
async def send_message(
    session_id: int,
    payload: ChatMessageCreate,
    current_user: User = Depends(get_current_user),
    service: ChatMessageService = Depends(get_chat_service),
) -> ApiResponse[ChatMessageOut]:
    """发送消息（非流式，返回完整响应）"""

    message = await service.send_message(current_user, session_id, payload)

    if not message:
        raise HTTPException(status_code=404, detail="会话不存在或无权限")

    return ApiResponse.ok(ChatMessageOut.model_validate(message))


@router.post("/sessions/{session_id}/messages/stream")
async def send_message_stream(
    session_id: int,
    payload: ChatMessageCreate,
    current_user: User = Depends(get_current_user),
    service: ChatMessageService = Depends(get_chat_service),
) -> StreamingResponse:
    """发送消息（流式响应，SSE）"""

    async def event_generator():
        try:
            async for token in service.send_message_stream(
                current_user, session_id, payload
            ):
                if token.startswith("Error:"):
                    yield f"data: {json.dumps({'error': token})}\n\n"
                    break
                else:
                    yield f"data: {json.dumps({'content': token})}\n\n"

            # 发送结束标记
            yield f"data: {json.dumps({'done': True})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
        },
    )


@router.get(
    "/sessions/{session_id}/messages",
    response_model=ApiResponse[ChatMessageListResponse],
)
async def get_message_history(
    session_id: int,
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    size: int = Query(20, ge=1, le=200, description="每页数量"),
    current_user: User = Depends(get_current_user),
    service: ChatMessageService = Depends(get_chat_service),
) -> ApiResponse[ChatMessageListResponse]:
    """查询消息历史（分页）"""

    items, total = await service.get_message_history(
        current_user, session_id, page=page, size=size
    )
    payload = ChatMessageListResponse(
        items=[ChatMessageOut.model_validate(item) for item in items],
        total=total,
        page=page,
        size=size,
    )
    return ApiResponse.ok(payload)
