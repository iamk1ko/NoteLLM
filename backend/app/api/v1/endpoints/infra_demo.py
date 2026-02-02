from __future__ import annotations

from fastapi import APIRouter, Depends
from aio_pika.abc import AbstractChannel
from minio import Minio
from redis.asyncio import Redis

from app.core.dependencies_infra import (
    get_minio,
    get_redis,
    get_rabbitmq_channel,
)
from app.schemas.response import ApiResponse
from app.core.settings import get_settings

router = APIRouter(tags=["infra_demo"])


@router.get("/infra/demo", response_model=ApiResponse[dict])
async def infra_demo(
    redis_client: Redis = Depends(get_redis),
    minio_client: Minio = Depends(get_minio),
    rabbit_channel: AbstractChannel = Depends(get_rabbitmq_channel),
) -> ApiResponse[dict]:
    """基础设施依赖注入演示接口。

    说明：
    - 演示 Redis / MinIO / RabbitMQ 的依赖注入方式
    - 仅做轻量调用，不影响业务数据
    """

    settings = get_settings()

    # Redis: ping
    redis_ok = await redis_client.ping()

    # MinIO: 查询桶是否存在（不创建）
    temp_bucket_exists = minio_client.bucket_exists(settings.MINIO_BUCKET_TEMP)

    # RabbitMQ: 声明一个测试队列（不发送消息）
    await rabbit_channel.declare_queue(settings.RABBITMQ_QUEUE, durable=True)

    return ApiResponse.ok(
        {
            "redis": bool(redis_ok),
            "minio_temp_bucket_exists": bool(temp_bucket_exists),
            "rabbitmq_queue": settings.RABBITMQ_QUEUE,
        }
    )
