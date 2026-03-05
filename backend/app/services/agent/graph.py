from __future__ import annotations

from typing import Any, AsyncGenerator, Awaitable, Callable

from langgraph.graph import END, StateGraph
from langgraph.types import RetryPolicy
from pydantic import BaseModel

from app.core.logging import get_logger
from app.services.agent.intent_classifier import IntentClassifier
from app.services.llm.service import LLMService
from app.services.memory.markdown_memory import MarkdownMemoryService
from app.services.vectorization.vector_store import MilvusVectorStore

logger = get_logger(__name__)


class AgentState(BaseModel):
    """
    Agent 状态对象，包含整个对话流程中需要传递和更新的数据。

        Attributes:
            - user_id: 用户 ID
            - session_id: 会话 ID
            - user_message: 用户输入的消息
            - file_id: 相关文件 ID（如果有的话）
            - history: 历史消息列表（从数据库加载）
            - long_term_memory: 长期记忆内容（从 Markdown 文件加载）
            - need_retrieval: 是否需要进行 RAG 检索（由意图分类器设置）
            - rag_context: RAG 检索到的上下文内容
            - prompt_messages: 最终构建的 LLM 提示消息列表
            - final_response: 最终生成的回复（可选，主要用于一次性调用）
    """
    user_id: int
    session_id: int
    user_message: str
    file_id: str | None
    history: list[dict] | None = None
    long_term_memory: str = ""
    need_retrieval: str = "yes"
    rag_context: str = ""
    prompt_messages: list[dict] | None = None
    final_response: str = ""


class ChatAgentGraph:
    def __init__(
            self,
            llm_service: LLMService,
            markdown_memory: MarkdownMemoryService,
            milvus: MilvusVectorStore | None,
            build_prompt: Any,
            rag_search: Any,
            load_history: Callable[[int], Awaitable[list[dict]]],
    ) -> None:
        self.llm_service = llm_service
        self.markdown_memory = markdown_memory
        self.milvus = milvus
        self.build_prompt = build_prompt
        self.rag_search = rag_search
        self.load_history = load_history
        self.intent_classifier = IntentClassifier(llm_service)

        self.graph = self._build_graph()

        # 显示Agent流程图（仅在开发环境中）
        # from IPython.display import Image, display
        # display(Image(self.graph.get_graph(xray=True).draw_mermaid_png()))

    def _build_graph(self):
        builder = StateGraph(AgentState)

        builder.add_node("classify_intent", self._classify_intent,
                         retry_policy=RetryPolicy(max_attempts=3, initial_interval=1.0))
        builder.add_node("load_history", self._load_history)
        builder.add_node("load_long_term_memory", self._load_long_term_memory,
                         retry_policy=RetryPolicy(max_attempts=3, initial_interval=1.0))
        builder.add_node("retrieve_rag", self._retrieve_rag)
        builder.add_node("build_prompt", self._build_prompt)

        builder.set_entry_point("classify_intent")
        builder.add_edge("classify_intent", "load_history")
        builder.add_edge("load_history", "load_long_term_memory")
        builder.add_conditional_edges(
            "load_long_term_memory",
            self._need_retrieval_branch,
            {"yes": "retrieve_rag", "no": "build_prompt"},
        )
        builder.add_edge("retrieve_rag", "build_prompt")
        builder.add_edge("build_prompt", END)

        return builder.compile()

    async def run(self, state: AgentState) -> AgentState:
        result: dict = await self.graph.ainvoke(state)
        return AgentState(**result)

    async def run_stream(self, state: AgentState) -> AsyncGenerator[str, None]:
        prepared_state: AgentState = await self.run(state)
        prompt_messages = prepared_state.prompt_messages or []

        async for token in self.llm_service.chat_stream(prompt_messages):
            yield token

    async def run_once(self, state: AgentState) -> str:
        prepared_state: AgentState = await self.run(state)
        prompt_messages = prepared_state.prompt_messages or []
        response = await self.llm_service.chat(prompt_messages)
        return response

    async def _classify_intent(self, state: AgentState) -> AgentState:
        logger.info("开始意图分类，用户消息: {}", state.user_message)
        need_retrieval = await self.intent_classifier.classify(state.user_message)
        logger.info("意图分类结果: {}", need_retrieval)
        state.need_retrieval = need_retrieval
        return state

    async def _load_history(self, state: AgentState) -> AgentState:
        state.history = await self.load_history(state.session_id)
        return state

    async def _load_long_term_memory(self, state: AgentState) -> AgentState:
        try:
            state.long_term_memory = await self.markdown_memory.load_memory(
                state.user_id, state.session_id
            )
        except Exception as e:
            logger.warning("长期记忆加载失败，降级为空: {}", e)
            state.long_term_memory = ""
        return state

    async def _retrieve_rag(self, state: AgentState) -> AgentState:
        if not state.file_id or not self.milvus:
            state.rag_context = ""
            return state
        try:
            state.rag_context = await self.rag_search(state.user_message, state.file_id)
        except Exception as e:
            logger.warning("RAG 检索失败，降级为空: {}", e)
            state.rag_context = ""
        return state

    async def _build_prompt(self, state: AgentState) -> AgentState:
        state.prompt_messages = self.build_prompt(
            state.user_message,
            state.rag_context,
            state.history or [],
            state.long_term_memory,
        )
        return state

    @staticmethod
    def _need_retrieval_branch(state: AgentState) -> str:
        return "yes" if state.need_retrieval == "yes" else "no"
