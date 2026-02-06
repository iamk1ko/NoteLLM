import os
from typing import Optional

import pytest


def _env(key: str) -> Optional[str]:
    # Load .env once (if python-dotenv is available) so os.getenv can read it
    if not getattr(_env, "_dotenv_loaded", False):
        try:
            from dotenv import load_dotenv, find_dotenv
            path = find_dotenv()
            if path:
                load_dotenv(path, override=False)
        except Exception:
            pass
        _env._dotenv_loaded = True
    value = os.getenv(key)
    return value.strip() if value else None


@pytest.mark.integration
def test_connect_redis():
    """Integration test for Redis connectivity.

    Required env vars:
      - REDIS_URL
    """

    redis_url = _env("REDIS_URL")
    if not redis_url:
        pytest.skip("REDIS_URL not set")

    import asyncio
    import redis.asyncio as redis

    async def _ping():
        client = redis.from_url(redis_url, decode_responses=True)
        print("\nRedis client created:", client)
        try:
            return await client.ping()
        finally:
            await client.aclose()

    assert asyncio.run(_ping()) is True


@pytest.mark.integration
def test_connect_minio():
    """Integration test for MinIO connectivity.

    Required env vars:
      - MINIO_ENDPOINT
      - MINIO_ACCESS_KEY
      - MINIO_SECRET_KEY
      - MINIO_SECURE
    """

    endpoint = _env("MINIO_ENDPOINT")
    access_key = _env("MINIO_ACCESS_KEY")
    secret_key = _env("MINIO_SECRET_KEY")
    secure = (_env("MINIO_SECURE") or "false").lower() == "true"

    if not endpoint or not access_key or not secret_key:
        pytest.skip("MINIO_ENDPOINT/MINIO_ACCESS_KEY/MINIO_SECRET_KEY not set")

    from minio import Minio

    client = Minio(
        endpoint, access_key=access_key, secret_key=secret_key, secure=secure
    )
    print("\nMinIO client created:", client)
    # list_buckets will raise if connection/auth fails
    buckets = client.list_buckets()
    assert buckets is not None


@pytest.mark.integration
def test_connect_rabbitmq():
    """Integration test for RabbitMQ connectivity.

    Required env vars:
      - RABBITMQ_URL
    """

    rabbit_url = _env("RABBITMQ_URL")
    if not rabbit_url:
        pytest.skip("RABBITMQ_URL not set")

    import asyncio
    import aio_pika

    async def _connect():
        connection = await aio_pika.connect_robust(rabbit_url)
        try:
            channel = await connection.channel()
            print("\nRabbitMQ channel created:", channel)
            await channel.close()
            return True
        finally:
            await connection.close()

    assert asyncio.run(_connect()) is True
