from __future__ import annotations

from typing import AsyncGenerator

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

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
        """
        创建 LLM 实例

        Notes:
            LangChain 会对某些已知参数（例如 max_tokens）发出告警：
            如果通过 model_kwargs 传入，会提示“应显式指定”。因此这里改为显式参数。
        """
        return ChatOpenAI(
            api_key=SecretStr(self.api_key),
            base_url=f"{self.base_url}/v1/",
            model=self.model,
            temperature=self.temperature,
            streaming=True,  # 启用流式输出
            max_tokens=self.max_tokens,
        )

    async def chat(self, messages: list[dict]) -> str:
        """同步调用 LLM，返回完整响应"""
        llm = self._create_llm()

        # 转换消息格式
        langchain_messages = self._convert_messages(messages)

        response = await llm.ainvoke(langchain_messages)
        # TODO: 这里还能优化，可以返回response对象，包含更多信息（如token使用量等），而不仅仅是content字符串
        return str(response.content)

    async def chat_stream(self, messages: list[dict]) -> AsyncGenerator[str, None]:
        """流式调用 LLM yield 每个 token"""
        llm = self._create_llm()

        # 转换消息格式
        langchain_messages = self._convert_messages(messages)

        async for chunk in llm.astream(langchain_messages):
            content = getattr(chunk, "content", "")
            if content:
                yield str(content)

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
