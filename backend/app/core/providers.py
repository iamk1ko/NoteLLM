from __future__ import annotations

from dataclasses import dataclass

from aio_pika.abc import AbstractRobustConnection
from minio import Minio
from redis.asyncio import Redis

from app.core.redis_client import get_redis_client
from app.core.rabbitmq_client import get_rabbitmq_connection, get_rabbitmq_queue_name
from app.core.minio_client import get_minio_client, get_minio_buckets, init_minio_buckets
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
        """初始化所有客户端。

        约定：
        - 这里“创建客户端对象并做必要的自检/初始化”，并把实例挂到 `app.state.infra`。
        - 注意：不要在模块 import 阶段做这些事（否则会产生导入副作用）。
        """

        try:
            # redis.asyncio 客户端创建是同步的，不需要 await。
            self.redis = get_redis_client()
        except Exception as e:
            logger.error(f"初始化 Redis 客户端失败: {e}")
            self.redis = None

        try:
            self.minio = get_minio_client()
            # 桶初始化是启动阶段的副作用操作：只在这里显式调用一次。
            init_minio_buckets(self.minio)
        except Exception as e:
            logger.error(f"初始化 MinIO 客户端失败: {e}")
            self.minio = None

        try:
            self.rabbitmq = await get_rabbitmq_connection()
        except Exception as e:
            logger.error(f"初始化 RabbitMQ 客户端失败: {e}")
            self.rabbitmq = None

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
            # redis.asyncio 新版推荐使用 aclose()；close() 仍可用但会有 DeprecationWarning。
            await self.redis.aclose()
            logger.info("Redis 客户端连接已关闭")

        if self.rabbitmq is not None:
            await self.rabbitmq.close()
            logger.info("RabbitMQ 客户端连接已关闭")

        # MinIO Python SDK 是基于 urllib3 的同步客户端，通常不需要显式 close。
        # 如果未来你改成自建 http pool/client，可以在这里统一关闭。
        logger.info("MinIO 客户端无需显式关闭（当前实现）")
        logger.info("基础设施客户端连接已全部关闭")
