from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.rabbitmq_client import (
    get_rabbitmq_connection,
    RABBITMQ_QUEUE_FILE_TASKS,
    RABBITMQ_QUEUE_VECTORIZE_TASKS,
    RABBITMQ_QUEUE_CHAT_MEMORY_TASKS
)
from app.dependencies.auth import get_current_user
from app.models import User
from app.schemas.response import ApiResponse

router = APIRouter(tags=["mq"])


@router.get("/mq/dlq")
async def get_dlq_metrics(
        current_user: User = Depends(get_current_user),
) -> ApiResponse[dict]:
    if current_user.role != "admin":
        return ApiResponse.error("Forbidden", code=403)

    connection = await get_rabbitmq_connection()
    channel = await connection.channel()
    try:
        dql_queue_names = [
            f"{RABBITMQ_QUEUE_FILE_TASKS}.dlq",
            f"{RABBITMQ_QUEUE_VECTORIZE_TASKS}.dlq",
            f"{RABBITMQ_QUEUE_CHAT_MEMORY_TASKS}.dlq",
        ]
        metrics = {}
        for name in dql_queue_names:
            queue = await channel.declare_queue(name, durable=True)
            metrics[name] = {
                "messages": queue.declaration_result.message_count,
                "consumers": queue.declaration_result.consumer_count,
            }
        return ApiResponse.ok(metrics)
    finally:
        await channel.close()
