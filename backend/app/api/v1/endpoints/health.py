from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_async_db
from app.schemas.response import ApiResponse

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> ApiResponse[dict]:
    """基础健康检查。

    说明：
    - 用于探活与快速验证服务可用性
    """

    return ApiResponse.ok({"status": "ok"})


@router.get("/health/detailed")
async def detailed_health_check(
    request: Request,
) -> ApiResponse[dict]:
    """详细健康检查。

    返回：
    - 各外部服务的连接状态
    - 数据库连接状态
    - 服务版本信息
    """
    from app.core.app_state import get_app_state
    from app.core.settings import get_settings

    settings = get_settings()
    state = get_app_state(request.app)
    infra = state.infra

    health_info = {
        "status": "ok",
        "app_name": settings.APP_NAME,
        "version": "1.0.0",
        "services": {},
    }

    # 检查 Redis
    if infra and infra.redis:
        try:
            pong = await infra.redis.ping()
            health_info["services"]["redis"] = "ok" if pong else "error"
        except Exception as e:
            health_info["services"]["redis"] = f"error: {str(e)}"
            health_info["status"] = "degraded"
    else:
        health_info["services"]["redis"] = "not_initialized"

    # 检查 MinIO
    if infra and infra.minio:
        try:
            health_info["services"]["minio"] = "ok"
        except Exception as e:
            health_info["services"]["minio"] = f"error: {str(e)}"
            health_info["status"] = "degraded"
    else:
        health_info["services"]["minio"] = "not_initialized"

    # 检查 Milvus
    if infra and infra.milvus:
        try:
            has_collection = await infra.milvus.has_collection()
            health_info["services"]["milvus"] = (
                "ok" if has_collection else "no_collection"
            )
        except Exception as e:
            health_info["services"]["milvus"] = f"error: {str(e)}"
            health_info["status"] = "degraded"
    else:
        health_info["services"]["milvus"] = "not_initialized"

    # 检查数据库
    try:
        db = get_async_db()
        async with db() as session:
            await session.execute("SELECT 1")
        health_info["services"]["database"] = "ok"
    except Exception as e:
        health_info["services"]["database"] = f"error: {str(e)}"
        health_info["status"] = "degraded"

    return ApiResponse.ok(health_info)
