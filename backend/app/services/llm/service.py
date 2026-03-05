from __future__ import annotations

from typing import AsyncGenerator, Literal

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from pydantic import SecretStr, BaseModel, Field

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

    def _create_llm(
            self,
            *,
            temperature: float | None = None,
            streaming: bool = True,
    ) -> ChatOpenAI:
        """
        创建 LLM 实例

        Notes:
            streaming=True 时用于流式输出。
        """
        return ChatOpenAI(
            api_key=SecretStr(self.api_key),
            base_url=f"{self.base_url}/v1/",
            model=self.model,
            temperature=self.temperature if temperature is None else temperature,
            streaming=streaming,
        )

    async def chat(self, messages: list[dict]) -> str:
        """同步调用 LLM，返回完整响应"""
        llm = self._create_llm(streaming=False)

        # 转换消息格式
        langchain_messages = self._convert_messages(messages)

        response = await llm.ainvoke(langchain_messages)
        # TODO: 这里还能优化，可以返回response对象，包含更多信息（如token使用量等），而不仅仅是content字符串
        return str(response.content)

    async def chat_stream(self, messages: list[dict]) -> AsyncGenerator[str, None]:
        """流式调用 LLM yield 每个 token"""
        llm = self._create_llm(streaming=True)

        # 转换消息格式
        langchain_messages = self._convert_messages(messages)

        async for chunk in llm.astream(langchain_messages):
            content = getattr(chunk, "content", "")
            if content:
                yield str(content)

    async def chat_with_overrides(
            self,
            messages: list[dict],
            *,
            temperature: float | None = None,
    ) -> str:
        class IntentClassification(BaseModel):
            need_retrieval: Literal["yes", "no"] = Field(..., description="是否需要进行RAG检索")

        """带参数覆盖的 LLM 调用，用于轻量分类场景"""
        llm = self._create_llm(
            streaming=False,
            temperature=temperature,
        ).with_structured_output(IntentClassification)

        langchain_messages = self._convert_messages(messages)
        response: IntentClassification = await llm.ainvoke(langchain_messages)
        return response.need_retrieval

    @staticmethod
    def _convert_messages(messages: list[dict]) -> list[BaseMessage]:
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
