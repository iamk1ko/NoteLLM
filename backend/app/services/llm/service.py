from __future__ import annotations

from typing import AsyncGenerator

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from langchain_classic.callbacks.streaming_aiter import AsyncIteratorCallbackHandler

from app.core.logging import get_logger

logger = get_logger(__name__)


class LLMService:
    """LLM 服务 - 调用 DeepSeek-V3.2 API"""

    def __init__(
            self,
            api_key: str,
            base_url: str,
            model: str = "DeepSeek-V3.2",
            temperature: float = 0.7,
            max_tokens: int = 2048,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.api_key = api_key
        self.base_url = base_url

    def _create_llm(self) -> ChatOpenAI:
        """创建 LLM 实例"""
        return ChatOpenAI(
            api_key=self.api_key,
            base_url=f"{self.base_url}/v1/",
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            streaming=True,  # 启用流式输出
        )

    async def chat(self, messages: list[dict]) -> str:
        """同步调用 LLM，返回完整响应"""
        llm = self._create_llm()

        # 转换消息格式
        langchain_messages = self._convert_messages(messages)

        response = await llm.ainvoke(langchain_messages)
        return response.content

    async def chat_stream(self, messages: list[dict]) -> AsyncGenerator[str, None]:
        """流式调用 LLM yield 每个 token"""
        llm = self._create_llm()

        # 转换消息格式
        langchain_messages = self._convert_messages(messages)

        # 创建回调处理器来捕获流式输出
        callback_handler = AsyncIteratorCallbackHandler()

        # 修改 llm 使用回调
        llm.callbacks = [callback_handler]

        # 异步任务：触发 LLM 调用
        import asyncio

        task = asyncio.create_task(llm.ainvoke(langchain_messages))

        # Yield 每一个 token
        async for token in callback_handler.aiter():
            yield token

        # 等待任务完成
        await task

    def _convert_messages(self, messages: list[dict]) -> list[BaseMessage]:
        """将字典格式的消息转换为 LangChain 消息对象"""
        result = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "user":
                result.append(HumanMessage(content=content))
            elif role == "assistant":
                result.append(AIMessage(content=content))
            elif role == "system":
                from langchain_core.messages import SystemMessage

                result.append(SystemMessage(content=content))
            # 其他角色默认作为用户消息

        return result


class LLMServiceError(Exception):
    """LLM 服务异常"""

    pass
