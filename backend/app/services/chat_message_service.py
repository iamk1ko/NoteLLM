from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncGenerator, Sequence
from typing import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import MilvusField
from app.core.logging import get_logger
from app.core.settings import get_settings
from app.prompts import load_prompt
from app.crud import ChatMessageCRUD, ChatSessionCRUD
from app.models import ChatMessage, User
from app.schemas.chat_message import ChatMessageCreate
from app.services.llm.service import LLMService
from app.services.memory.markdown_memory import MarkdownMemoryService
from app.services.memory.redis_memory import RedisChatMemory
from app.services.vectorization.embedder import BgeM3Embedder
from app.services.vectorization.vector_store import MilvusVectorStore

logger = get_logger(__name__)

SYSTEM_PROMPT = load_prompt("chat_system.txt")
USER_PROMPT_TEMPLATE = load_prompt("chat_user.txt")


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

        await self.redis_memory_factory(session_id).append_message(
            {
                "id": user_message.id,
                "session_id": user_message.session_id,
                "user_id": user_message.user_id,
                "role": user_message.role,
                "content": user_message.content,
                "model_name": user_message.model_name,
                "token_count": user_message.token_count,
                "create_time": user_message.create_time.isoformat()
                if user_message.create_time
                else "",
            }
        )
        logger.debug(
            "保存用户消息完成: session_id={}, user_id={}, msg_id={}",
            session_id,
            user.id,
            user_message.id,
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
            model_name=get_settings().LLM_MODEL,
        )

        await self.redis_memory_factory(session_id).append_message(
            {
                "id": ai_message.id,
                "session_id": ai_message.session_id,
                "user_id": ai_message.user_id,
                "role": ai_message.role,
                "content": ai_message.content,
                "model_name": ai_message.model_name,
                "token_count": ai_message.token_count,
                "create_time": ai_message.create_time.isoformat()
                if ai_message.create_time
                else "",
            }
        )
        logger.debug(
            "保存 AI 消息完成: session_id={}, user_id={}, msg_id={}",
            session_id,
            user.id,
            ai_message.id,
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

        # 验证会话权限
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

        # 将用户消息追加到 Redis 中
        await self.redis_memory_factory(session_id).append_message(
            {
                "id": user_message.id,
                "session_id": user_message.session_id,
                "user_id": user_message.user_id,
                "role": user_message.role,
                "content": user_message.content,
                "model_name": user_message.model_name,
                "token_count": user_message.token_count,
                "create_time": user_message.create_time.isoformat()
                if user_message.create_time
                else "",
            }
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
                model_name=get_settings().LLM_MODEL,
            )

            # 将 AI 消息追加到 Redis 中
            await self.redis_memory_factory(session_id).append_message(
                {
                    "id": ai_message.id,
                    "session_id": ai_message.session_id,
                    "user_id": ai_message.user_id,
                    "role": ai_message.role,
                    "content": ai_message.content,
                    "model_name": ai_message.model_name,
                    "token_count": ai_message.token_count,
                    "create_time": ai_message.create_time.isoformat()
                    if ai_message.create_time
                    else "",
                }
            )
            total_elapsed = int((time.time() - start_time) * 1000)
            logger.info(
                "流式消息成功: session_id={}, user_id={}, ai_msg_id={}, "
                "总耗时={} s, 调用LLM耗时={}, token数量={}, 相应消息总长度={}",
                session_id,
                user.id,
                ai_message.id,
                total_elapsed / 1000,  # 转换为秒
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
        redis_memory = self.redis_memory_factory(session_id)
        if not await redis_memory.has_cache():
            await redis_memory.load_from_mysql(self.db)

        items, total = await redis_memory.get_messages_page(page, size)
        if total > 0:
            return self._coerce_message_models(items), total

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

    def _coerce_message_models(self, items: list[dict]) -> list[ChatMessage]:
        messages: list[ChatMessage] = []
        for item in items:
            msg = ChatMessage()
            for key, value in item.items():
                setattr(msg, key, value)
            messages.append(msg)
        return messages

    async def _generate_ai_response(
            self,
            user_id: int,
            session_id: int,
            user_message: str,
            file_id: str | None,
    ) -> str:
        redis_memory = self.redis_memory_factory(session_id)
        if not await redis_memory.has_cache():
            await redis_memory.load_from_mysql(self.db)
        history = await redis_memory.get_context_for_llm()

        evidence = await self._rag_search(user_message, file_id)

        try:
            long_term_memory = await self.markdown_memory.load_memory(
                user_id, session_id
            )
        except Exception as e:
            logger.warning("长期记忆加载失败，降级为短期记忆: {}", e)
            long_term_memory = ""

        prompt_messages = self._build_prompt(
            user_message, evidence, history, long_term_memory
        )
        response = await self.llm_service.chat(prompt_messages)

        # Redis 已在创建消息时写入，无需重复写入

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
        redis_memory: RedisChatMemory = self.redis_memory_factory(session_id)
        if not await redis_memory.has_cache():
            await redis_memory.load_from_mysql(self.db)
        history = await redis_memory.get_context_for_llm()

        evidence = await self._rag_search(user_message, file_id)

        try:
            long_term_memory = await self.markdown_memory.load_memory(
                user_id, session_id
            )
        except Exception as e:
            logger.warning("长期记忆加载失败，降级为短期记忆。错误信息: {}", e)
            long_term_memory = ""

        prompt_messages = self._build_prompt(
            user_message, evidence, history, long_term_memory
        )

        full_response = ""
        async for token in self.llm_service.chat_stream(prompt_messages):
            full_response += token
            yield token

        # TODO: 这里可以优化使用rabbitmq等消息队列来异步处理长期记忆更新，避免在主流程中创建过多的asyncio任务
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
            filters = (
                {MilvusField.FILE_ID.value: int(file_id)} if file_id.isdigit() else None
            )

            query_vector = self.embedder.encode_queries([query])["dense"][0]
            logger.info(
                "RAG 查询 (即用户输入) 向量化完成: query='{}', vector_dim={}",
                query,
                len(query_vector),
            )

            results = await self.milvus.search_hybrid(
                query=query,
                query_vector=query_vector,
                k=settings.RAG_TOP_K,
                filters=filters,
                alpha=settings.RAG_RANKER_ALPHA,
            )
            logger.info(
                "RAG 混合检索完成: query='{}', top_k={}, raw_results={}",
                query,
                settings.RAG_TOP_K,
                results,
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

    async def _update_long_term_memory(self, user_id: int, session_id: int, user_message: str, ai_response: str):
        try:
            prompt = load_prompt("memory_update.txt").format(
                user_message=user_message,
                assistant_message=ai_response,
            )
            summary_text = await self.llm_service.chat(
                [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ]
            )
            updates = self._parse_summary_updates(summary_text)
            await self.markdown_memory.apply_updates(user_id, session_id, updates)
        except Exception as e:
            logger.error("长期记忆更新失败: {}", e)

    def _build_prompt(
            self,
            user_message: str,
            evidence: str,
            history: list[dict],
            long_term_memory: str,
    ) -> list[dict]:
        """
        构建 LLM 输入的 prompt，整合用户消息、RAG 证据、历史对话和长期记忆

        Args:
            user_message: 当前用户输入的消息内容
            evidence: RAG 检索到的相关证据文本
            history: 从 Redis 获取的历史对话消息列表，每条消息包含 role 和 content
            long_term_memory: 从 Markdown 存储加载的长期记忆内容，包含角色设定、任务描述、状态信息等

        Returns:
            LLM 输入的消息列表，每条消息包含 role 和 content，按照系统提示 + 用户提示的格式构建
        """
        history_str = ""
        if history:
            parts: list[str] = []
            for msg in history:
                role = "user" if msg["role"] == "user" else "assistant"
                parts.append(f"**role**: {role}\n**content**: {msg['content']}")
            history_str = "\n\n-----------------------------\n\n".join(parts)

        memory_sections = self._parse_long_term_memory(long_term_memory)
        memory_limit = get_settings().REDIS_MEMORY_LIMIT
        prompt_text = USER_PROMPT_TEMPLATE.format(
            role_policies=memory_sections.get("role_policies")
                          or "你是一个专业的AI助手。",
            task=memory_sections.get("task") or "回答用户问题。",
            state=memory_sections.get("state") or "暂无",
            rag_context=evidence or "（无检索结果）",
            history=history_str or "（无历史对话）",
            history_limit=memory_limit,
            user_message=user_message,
            output=memory_sections.get("output") or "直接输出回答内容。",
        )

        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt_text},
        ]

    def _parse_long_term_memory(self, content: str) -> dict[str, str]:
        sections = {
            "role_policies": "",
            "task": "",
            "state": "",
            "output": "",
        }
        if not content:
            return sections

        current_key = ""
        for line in content.split("\n"):
            header = line.strip().lower()
            if header.startswith("# role"):
                current_key = "role_policies"
                continue
            if header.startswith("# task"):
                current_key = "task"
                continue
            if header.startswith("# state"):
                current_key = "state"
                continue
            if header.startswith("# output"):
                current_key = "output"
                continue
            if current_key:
                sections[current_key] += line + "\n"

        return {k: v.strip() for k, v in sections.items()}

    def _parse_summary_updates(self, content: str) -> dict[str, str]:
        sections = {
            "role_policies": "",
            "task": "",
            "state": "",
            "output": "",
        }
        if not content:
            return sections

        current_key = ""
        for line in content.split("\n"):
            header = line.strip().lower()
            if header.startswith("role"):
                current_key = "role_policies"
                continue
            if header.startswith("task"):
                current_key = "task"
                continue
            if header.startswith("state"):
                current_key = "state"
                continue
            if header.startswith("output"):
                current_key = "output"
                continue
            if current_key:
                sections[current_key] += line + "\n"

        return {k: v.strip() for k, v in sections.items()}
