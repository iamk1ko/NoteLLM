from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncGenerator, Sequence
from typing import Any, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.settings import get_settings
from app.crud import ChatMessageCRUD, ChatSessionCRUD
from app.models import ChatMessage, User
from app.schemas.chat_message import ChatMessageCreate
from app.services.llm.service import LLMService
from app.services.memory.markdown_memory import MarkdownMemoryService
from app.services.memory.redis_memory import RedisChatMemory
from app.services.vectorization.vector_store import MilvusVectorStore
from app.services.vectorization.embedder import Embedder, BgeM3Embedder

logger = get_logger(__name__)

RAG_PROMPT_TEMPLATE = """# 知识库检索结果

{context}

---

# 对话历史

{history}

---

# 当前问题

{question}

---

请根据上面的知识库检索结果和对话历史，回答用户的问题。
如果知识库中没有相关信息，请如实说明。
"""


class ChatMessageService:
    def __init__(
            self,
            db: AsyncSession,
            llm_service: LLMService,
            redis_memory_factory: Callable[[int], RedisChatMemory],
            markdown_memory: MarkdownMemoryService,
            milvus: MilvusVectorStore | None = None,
            embedder: BgeM3Embedder | None = None,
    ):
        self.db = db
        self.llm_service = llm_service
        self.redis_memory_factory = redis_memory_factory
        self.markdown_memory = markdown_memory
        self.milvus = milvus
        self.embedder = embedder

    async def send_message(
            self, user: User, session_id: int, payload: ChatMessageCreate
    ) -> ChatMessage | None:
        start_time = time.time()

        session = await self._get_session(user, session_id)
        if not session:
            logger.warning(
                "发送消息失败：会话不存在或无权限 session_id={}, user_id={}",
                session_id,
                user.id,
            )
            return None

        # 1. 保存用户消息到数据库
        user_message = await ChatMessageCRUD.create_message_async(
            db=self.db,
            session_id=session_id,
            user_id=user.id,
            content=payload.content,
            role="user",
            model_name=payload.model_name,
        )
        logger.debug(
            "保存用户消息完成: session_id={}, user_id={}, msg_id={}",
            session_id,
            user.id,
            user_message.id
        )

        # 2. 调用 LLM 生成响应（整合 RAG）
        llm_start = time.time()
        ai_response = await self._generate_ai_response(
            user_id=user.id,
            session_id=session_id,
            user_message=payload.content,
            file_id=session.context_id,
        )
        llm_elapsed = int((time.time() - llm_start) * 1000)

        # 3. 保存 AI 响应到数据库
        ai_message = await ChatMessageCRUD.create_message_async(
            db=self.db,
            session_id=session_id,
            user_id=user.id,
            content=ai_response,
            role="assistant",
            model_name="DeepSeek-V3.2",
        )
        logger.debug(
            "保存 AI 消息完成: session_id={}, user_id={}, msg_id={}",
            session_id,
            user.id,
            ai_message.id
        )

        total_elapsed = int((time.time() - start_time) * 1000)
        logger.info(
            "发送消息成功: session_id={}, user_id={}, user_msg_id={}, ai_msg_id={}, "
            "总耗时={}, 调用LLM耗时={}, 相应消息总长度={}",
            session_id,
            user.id,
            user_message.id,
            ai_message.id,
            total_elapsed,
            llm_elapsed,
            len(ai_response),
        )

        return ai_message

    async def send_message_stream(
            self, user: User, session_id: int, payload: ChatMessageCreate
    ) -> AsyncGenerator[str, None]:
        start_time = time.time()

        session = await self._get_session(user, session_id)
        if not session:
            logger.warning(
                "发送消息失败：会话不存在或无权限 session_id={}, user_id={}",
                session_id,
                user.id,
            )
            yield "Error: 会话不存在或无权限"
            return

        # 保存用户消息到数据库
        user_message = await ChatMessageCRUD.create_message_async(
            db=self.db,
            session_id=session_id,
            user_id=user.id,
            content=payload.content,
            role="user",
            model_name=payload.model_name,
        )
        logger.debug(
            "保存用户消息完成: session_id={}, user_id={}, msg_id={}",
            session_id,
            user.id,
            user_message.id,
        )

        # 流式调用 LLM，同时yield每个token
        full_response = ""
        token_count = 0
        llm_start = time.time()

        try:
            async for token in self._generate_ai_response_stream(
                    user_id=user.id,
                    session_id=session_id,
                    user_message=payload.content,
                    file_id=session.context_id,
            ):
                full_response += token
                token_count += 1
                yield token
            llm_elapsed = int((time.time() - llm_start) * 1000)
        except Exception as e:
            logger.error(
                "LLM 流式响应失败: session_id={}, user_id={}, error={}",
                session_id,
                user.id,
                e,
            )
            yield f"Error: {str(e)}"
            return

        # 保存 AI 响应到数据库
        if full_response:
            ai_message = await ChatMessageCRUD.create_message_async(
                db=self.db,
                session_id=session_id,
                user_id=user.id,
                content=full_response,
                role="assistant",
                model_name="DeepSeek-V3.2",
            )
            total_elapsed = int((time.time() - start_time) * 1000)
            logger.info(
                "流式消息成功: session_id={}, user_id={}, ai_msg_id={}, "
                "总耗时={}, 调用LLM耗时={}, token数量={}, 相应消息总长度={}",
                session_id,
                user.id,
                ai_message.id,
                total_elapsed,
                llm_elapsed,
                token_count,
                len(full_response),
            )

    async def get_message_history(
            self,
            user: User,
            session_id: int,
            page: int = 1,
            size: int = 20,
    ) -> tuple[Sequence[ChatMessage], int]:
        if user.role == "admin":
            return await ChatMessageCRUD.get_session_messages_async(
                db=self.db, session_id=session_id, page=page, size=size
            )
        return await ChatMessageCRUD.get_user_session_messages_async(
            db=self.db,
            session_id=session_id,
            user_id=user.id,
            page=page,
            size=size,
        )

    async def _get_session(self, user: User, session_id: int):
        if user.role == "admin":
            return await ChatSessionCRUD.get_session_by_id_async(self.db, session_id)
        return await ChatSessionCRUD.get_user_session_async(
            self.db, session_id, user.id
        )

    async def _generate_ai_response(
            self,
            user_id: int,
            session_id: int,
            user_message: str,
            file_id: str | None,
    ) -> str:
        redis_memory = self.redis_memory_factory(session_id)
        await redis_memory.load_from_mysql(self.db)  # 加载历史到 Redis，首次加载会从 MySQL 获取，后续请求会直接使用 Redis 缓存
        history = await redis_memory.get_context_for_llm()  # 从 Redis 获取 10 条对话历史，格式化为 LLM 上下文

        context = await self._rag_search(user_message, file_id)

        long_term_memory = await self.markdown_memory.load_memory(user_id, session_id)

        prompt_messages = self._build_prompt(
            user_message, context, history, long_term_memory
        )
        response = await self.llm_service.chat(prompt_messages)

        await redis_memory.append_message("user", user_message)
        await redis_memory.append_message("assistant", response)

        asyncio.create_task(
            self._update_long_term_memory(user_id, session_id, user_message, response)
        )

        return response

    async def _generate_ai_response_stream(
            self,
            user_id: int,
            session_id: int,
            user_message: str,
            file_id: str | None,
    ) -> AsyncGenerator[str, None]:
        redis_memory = self.redis_memory_factory(session_id)
        await redis_memory.load_from_mysql(self.db)
        history = await redis_memory.get_context_for_llm()

        context = await self._rag_search(user_message, file_id)

        long_term_memory = await self.markdown_memory.load_memory(user_id, session_id)

        # TODO: 这里还有待优化，目前会把长期记忆直接拼接到 prompt 中，后续可以改为在生成过程中动态调用长期记忆接口，或者在 RAG 检索结果中加入长期记忆摘要
        prompt_messages = self._build_prompt(
            user_message, context, history, long_term_memory
        )

        full_response = ""
        async for token in self.llm_service.chat_stream(prompt_messages):
            full_response += token
            yield token

        await redis_memory.append_message("user", user_message)
        await redis_memory.append_message("assistant", full_response)

        asyncio.create_task(
            self._update_long_term_memory(
                user_id, session_id, user_message, full_response
            )
        )

    async def _rag_search(self, query: str, file_id: str | None) -> str:
        if not file_id or not self.milvus or not self.embedder:
            return ""

        try:
            settings = get_settings()
            filters = {"file_id": int(file_id)} if file_id.isdigit() else None

            query_vector = self.embedder.encode_queries([query])["dense"][0]
            results = await self.milvus.search_hybrid(
                query=query,
                query_vector=query_vector,
                k=settings.RAG_TOP_K,
                filters=filters,
                alpha=settings.RAG_RANKER_ALPHA,
            )

            if results:
                context = "\n\n".join(
                    [
                        f"【来源 {i + 1}】{r.get('text', r.get('content', ''))}"
                        for i, r in enumerate(results)
                    ]
                )
                logger.info("RAG 检索到 {} 条结果", len(results))
                return context

        except Exception as e:
            logger.warning("RAG 检索失败: {}", e)

        return ""

    async def _update_long_term_memory(
            self, user_id: int, session_id: int, user_message: str, ai_response: str
    ):
        try:
            await self.markdown_memory.append_summary(
                user_id, session_id, user_message, ai_response
            )
        except Exception as e:
            logger.error("长期记忆更新失败: {}", e)

    def _build_prompt(
            self,
            user_message: str,
            context: str,
            history: list[dict],
            long_term_memory: str,
    ) -> list[dict]:
        history_str = ""
        if history:
            for msg in history:
                role = "用户" if msg["role"] == "user" else "AI"
                history_str += f"{role}: {msg['content']}\n\n"

        prompt_text = RAG_PROMPT_TEMPLATE.format(
            context=context or "（无检索结果）",
            history=history_str or "（无历史对话）",
            question=user_message,
        )

        if long_term_memory:
            prompt_text += f"\n\n---\n\n# 历史摘要\n\n{long_term_memory}"

        return [
            {
                "role": "system",
                "content": "你是一个专业的AI助手，请根据提供的知识库和对话历史来回答用户的问题。",
            },
            {"role": "user", "content": prompt_text},
        ]
