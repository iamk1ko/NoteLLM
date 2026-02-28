from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

import aio_pika
from aio_pika.abc import AbstractChannel, AbstractIncomingMessage, AbstractExchange

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class RetryTopology:
    """
    定义一个带重试和死信机制的 RabbitMQ 拓扑结构的数据类。
        - queue_name: 主队列名称。
        - retry_queue_name: 重试队列名称。
        - dlq_name: 死信队列名称。
        - retry_exchange: 用于重试的交换机。
        - dlx_exchange: 用于死信的交换机。
        这个数据类封装了与重试和死信机制相关的所有信息，方便在消费者中使用。
    """
    queue_name: str
    retry_queue_name: str
    dlq_name: str
    retry_exchange: AbstractExchange
    dlx_exchange: AbstractExchange


async def declare_retry_topology(
        channel: AbstractChannel,
        queue_name: str,
        retry_ttl_ms: int,
) -> RetryTopology:
    """
    声明一个带重试和死信机制的 RabbitMQ 拓扑结构。包括：
        1. 主队列：正常消费的队列，声明时指定死信交换机和路由键（重试到 retry_exchange）。
        2. 重试交换机和重试队列：重试交换机用于接收主队列的死信，重试队列声明时指定 TTL 和死信交换机/路由键（重试到主队列）。
        3. 死信交换机和死信队列：死信交换机用于接收超过重试次数的消息，死信队列绑定到死信交换机。



    Args:
        channel: 已连接的 RabbitMQ 频道。
        queue_name: 主队列名称。
        retry_ttl_ms: 重试队列中消息的 TTL（毫秒）。
    Returns:
        RetryTopology (重试拓扑) 对象，包含相关队列和交换机的信息。
    """

    # 声明重试交换机和死信交换机：
    retry_exchange = await channel.declare_exchange(
        f"{queue_name}.retry.exchange",
        aio_pika.ExchangeType.DIRECT,
        durable=True,
    )
    dlx_exchange = await channel.declare_exchange(
        f"{queue_name}.dlx.exchange",
        aio_pika.ExchangeType.DIRECT,
        durable=True,
    )

    # 主队列声明时指定死信交换机/路由键：
    await channel.declare_queue(
        queue_name,
        durable=True,
        arguments={
            "x-dead-letter-exchange": retry_exchange.name,
            "x-dead-letter-routing-key": queue_name,
        },
    )

    # 重试队列声明时指定 TTL 和死信交换机/路由键（重试到主队列）：
    retry_queue_name = f"{queue_name}.retry"
    retry_queue = await channel.declare_queue(
        retry_queue_name,
        durable=True,
        arguments={
            "x-message-ttl": retry_ttl_ms,
            "x-dead-letter-exchange": "",
            "x-dead-letter-routing-key": queue_name,
        },
    )
    await retry_queue.bind(retry_exchange, routing_key=queue_name)

    # 死信队列声明并绑定到死信交换机：
    dlq_name = f"{queue_name}.dlq"
    dlq_queue = await channel.declare_queue(dlq_name, durable=True)
    await dlq_queue.bind(dlx_exchange, routing_key=queue_name)

    # 返回封装了拓扑信息的 RetryTopology 对象：
    return RetryTopology(
        queue_name=queue_name,
        retry_queue_name=retry_queue_name,
        dlq_name=dlq_name,
        retry_exchange=retry_exchange,
        dlx_exchange=dlx_exchange,
    )


def get_retry_count(message: AbstractIncomingMessage, queue_name: str) -> int:
    headers = message.headers or {}
    x_death = headers.get("x-death")
    if isinstance(x_death, list):
        for entry in x_death:
            if entry.get("queue") == queue_name:
                return int(entry.get("count", 0))
    return 0


async def handle_with_retry(
        message: AbstractIncomingMessage,
        queue_name: str,
        handler: Callable[[dict[str, Any]], Awaitable[None]],
        topology: RetryTopology,
        max_retries: int,
) -> None:
    """
    处理消息并根据结果进行重试或死信投递。处理流程：
        1. 尝试调用 handler 处理消息。
        2. 如果处理成功，ack 消息。
        3. 如果处理失败，获取当前重试次数。
        4. 如果重试次数超过 max_retries，将消息投递到死信交换机，并 ack 原消息。
        5. 如果重试次数未超过 max_retries，nack 原消息（不重入队列），让其进入重试流程。
    通过这种方式，我们实现了一个基于 RabbitMQ 的可靠消息处理机制，支持自动重试和死信投递，确保消息不会丢失且能够在处理失败时得到适当的处理。

    Args:
        message: 收到的 RabbitMQ 消息。
        queue_name: 主队列名称（用于获取重试次数）。
        handler: 处理消息的异步函数，接受解码后的消息体（dict）作为参数。
        topology: RetryTopology 对象，包含重试和死信相关的交换机信息。
        max_retries: 最大重试次数，超过后消息将被投递到死信队列。

    Returns:
        None
    """
    try:
        payload: dict[str, Any] = json.loads(message.body.decode("utf-8"))
        await handler(payload)
        await message.ack()
    except Exception as e:
        retry_count = get_retry_count(message, queue_name)
        if retry_count >= max_retries:
            await topology.dlx_exchange.publish(
                aio_pika.Message(body=message.body, headers=message.headers or {}),
                routing_key=queue_name,
            )
            logger.error(
                "消息处理失败，投递死信队列: queue={}, retry_count={}, error={}",
                queue_name,
                retry_count,
                e,
            )
            await message.ack()
        else:
            logger.warning(
                "消息处理失败，进入重试: queue={}, retry_count={}, error={}",
                queue_name,
                retry_count,
                e,
            )
            await message.nack(requeue=False)
