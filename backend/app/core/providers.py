from __future__ import annotations

from dataclasses import dataclass

from aio_pika.abc import AbstractRobustConnection
from minio import Minio
from redis.asyncio import Redis

from app.core.redis_client import get_redis_client
from app.core.rabbitmq_client import get_rabbitmq_connection, get_rabbitmq_queue_name
from app.core.minio_client import get_minio_client, get_minio_buckets
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class InfraProvider:
    """基础设施客户端 Provider（类似 Spring Bean）。

    说明：
    - 统一初始化 Redis/MinIO/RabbitMQ 客户端
    - 在应用启动时创建，在关闭时释放
    """

    redis: Redis | None = None
    minio: Minio | None = None
    rabbitmq: AbstractRobustConnection | None = None

    async def init(self) -> None:
        """初始化所有客户端。"""

        self.redis = get_redis_client()
        self.minio = get_minio_client()
        self.rabbitmq = await get_rabbitmq_connection()

        if self.redis is None:
            raise RuntimeError("无法初始化 Redis 客户端连接")
        if self.minio is None:
            raise RuntimeError("无法初始化 MinIO 客户端连接")
        if self.rabbitmq is None:
            raise RuntimeError("无法初始化 RabbitMQ 客户端连接")

        logger.info("基础设施客户端（Redis、MinIO、RabbitMQ）初始化完成")

    async def self_check(self) -> dict[str, bool]:
        """启动自检，确认各服务可用。

        说明：
        - Redis: ping
        - MinIO: 检查临时桶是否存在
        - RabbitMQ: 声明默认队列
        """

        results = {
            "redis": False,
            "minio": False,
            "rabbitmq": False,
        }

        # Redis
        if self.redis is not None:
            try:
                results["redis"] = bool(await self.redis.ping())
            except Exception:
                results["redis"] = False

        # MinIO
        if self.minio is not None:
            try:
                temp_bucket, _ = get_minio_buckets()
                results["minio"] = bool(self.minio.bucket_exists(temp_bucket))
            except Exception:
                results["minio"] = False

        # RabbitMQ
        if self.rabbitmq is not None:
            try:
                queue_name = await get_rabbitmq_queue_name()
                channel = await self.rabbitmq.channel()
                await channel.declare_queue(queue_name, durable=True)
                await channel.close()
                results["rabbitmq"] = True
            except Exception:
                results["rabbitmq"] = False

        return results

    async def close(self) -> None:
        """关闭所有客户端连接。"""

        if self.redis is not None:
            await self.redis.close()
            logger.info("Redis 客户端连接已关闭")
        if self.rabbitmq is not None:
            await self.rabbitmq.close()
            logger.info("RabbitMQ 客户端连接已关闭")
        logger.info("基础设施客户端连接已全部关闭")
