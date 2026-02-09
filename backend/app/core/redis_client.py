from __future__ import annotations

import redis.asyncio as redis
from redis.asyncio import Redis

from app.core.settings import get_settings

"""
FILE_STORAGE_METADATA_KEY: 
    可以用于监控和调试，记录上传文件的元数据信息（如文件名、总分片数、已上传分片数等），以便在合并分片时进行校验和状态更新。
    此外，可以用于给前端反应用户上传文件的状态。例如：
        - `UPLOADED` 表示 `文件已上传，后台正在建立知识库中...`
        - `EMBEDDED` 表示 `文件已上传并完成知识库建立`
        - `FAILED` 表示 `文件上传失败或知识库建立失败`
        
UPLOAD_FILE_CHUNKS_BITMAP_KEY:
    适用于大文件分片上传的场景，可以使用 Redis Bitmap 来高效地记录每个分片的上传状态（已上传/未上传）。例如：
        - 当用户上传一个大文件时，后端可以根据文件大小和分片大小计算出总分片数，并在 Redis 中创建一个 Bitmap。
        - 每当一个分片上传成功后，后端就将对应 Bitmap 位设置为 1。
        - 在合并分片之前，后端可以检查 Bitmap 来确认所有分片是否都已上传完成。
        
FILE_VECTORIZATION_KEY:
    用于记录文件向量化任务的状态，避免重复向量化同一文件。例如：
        - 当一个文件上传完成后，后端会将对应的向量化任务状态设置为 `running`。
        - 当向量化任务完成后，状态更新为 `success` 或 `failed`。
        - 在接收到新的向量化请求时，后端可以先检查 Redis 中的状态，如果已经是 `success` 则直接返回结果
"""
FILE_STORAGE_METADATA_KEY: str = "file_storage:meta:{}:{}"  # 格式化参数：user_id, file_md5
UPLOAD_FILE_CHUNKS_BITMAP_KEY: str = "upload:bitmap:{}:{}"  # 格式化参数：user_id, file_md5
FILE_VECTORIZATION_KEY: str = "vector:task:{}"  # 格式化参数：file_md5


def get_redis_client() -> Redis:
    """创建 Redis 异步客户端对象。

    说明（很关键）：
    - 这个函数只是“构造客户端对象/连接池配置”，通常不会在这里立刻发起网络连接。
    - 真实的网络连接一般发生在你第一次执行命令时（比如 `await client.ping()`）。
    - 因此它是“无副作用”的，适合在 lifespan 中创建并缓存。

    连接信息来自：Settings.REDIS_URL
    """

    settings = get_settings()
    return redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        max_connections=settings.REDIS_MAX_CONNECTIONS,
    )
