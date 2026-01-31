from fastapi import APIRouter

from app.schemas.response import ApiResponse

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> ApiResponse[dict]:
    """健康检查。

    说明：
    - 用于探活与快速验证服务可用性
    """

    return ApiResponse.ok({"status": "ok"})
