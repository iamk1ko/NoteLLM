from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncGenerator, Sequence
from typing import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.crud import ChatMessageCRUD, ChatSessionCRUD
from app.models import ChatMessage, User
from app.schemas.chat_message import ChatMessageCreate
from app.services.llm.service import LLMService
from app.services.memory.markdown_memory import MarkdownMemoryService
from app.services.memory.redis_memory import RedisChatMemory
from app.services.rag import RagResult

logger = get_logger(__name__)

# Prompt 模板
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
    """聊天消息业务服务层（异步版） - 集成 RAG + LLM"""

    def __init__(
            self,
            db: AsyncSession,
            llm_service: LLMService | None = None,
            redis_memory_factory: Callable[[int], RedisChatMemory] | None = None,
            markdown_memory: MarkdownMemoryService | None = None,
            rag_service_factory: Callable | None = None,
    ):
        """初始化服务

        Args:
            db: 数据库会话
            llm_service: LLM 服务实例（可选，默认从配置创建）
            redis_memory_factory: Redis 记忆工厂函数（可选）
            markdown_memory: Markdown 记忆服务实例（可选）
            rag_service_factory: RAG 服务工厂函数（可选）
        """
        self.db = db
        self._llm_service = llm_service
        self._redis_memory_factory = redis_memory_factory
        self._markdown_memory = markdown_memory
        self._rag_service_factory = rag_service_factory

    def _get_llm_service(self) -> LLMService:
        """获取 LLM 服务实例"""
        if self._llm_service is None:
            from app.services.llm.service import LLMService
            from app.core.settings import get_settings

            settings = get_settings()
            if not settings.BLSC_API_KEY or not settings.BLSC_BASE_URL:
                raise RuntimeError("LLM not configured")

            self._llm_service = LLMService(
                api_key=settings.BLSC_API_KEY,
                base_url=settings.BLSC_BASE_URL,
                model=settings.LLM_MODEL,
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
            )
        return self._llm_service

    def _get_redis_memory(self, session_id: int) -> RedisChatMemory:
        """获取 Redis 记忆实例"""
        if self._redis_memory_factory:
            return self._redis_memory_factory(session_id)

        # 默认创建
        from app.core.redis_client import get_redis_client

        redis_client = get_redis_client()
        return RedisChatMemory(redis_client, session_id, memory_limit=10)

    def _get_markdown_memory(self) -> MarkdownMemoryService:
        """获取 Markdown 记忆实例"""
        if self._markdown_memory:
            return self._markdown_memory

        from app.core.minio_client import get_minio_client

        minio_client = get_minio_client()
        return MarkdownMemoryService(minio_client)

    async def _get_rag_service(self):
        """获取 RAG 服务实例"""
        if self._rag_service_factory:
            return await self._rag_service_factory(self.db)

        try:

            # 直接创建 Redis 客户端（不使用 Depends）
            from app.core.redis_client import get_redis_client

            redis_client = get_redis_client()

            # 从 app.state 获取 Milvus
            # 由于无法直接获取 app，这里暂时禁用 RAG 服务
            # TODO: 应该在路由层注入 RAG 服务
            logger.warning("RAG 服务无法获取 Milvus 实例，跳过 RAG 检索")
            return None

        except Exception as e:
            logger.error("获取 RAG 服务失败: {}", e)
            return None

    async def send_message(
            self, user: User, session_id: int, payload: ChatMessageCreate
    ) -> ChatMessage | None:
        """发送消息（非流式，返回完整响应）"""
        start_time = time.time()

        # 权限检查
        session = await self._get_session(user, session_id)
        if not session:
            logger.warning(
                "发送消息失败：会话不存在或无权限 session_id={}, user_id={}",
                session_id,
                user.id,
            )
            return None

        # 1. 保存用户消息到数据库
        save_time = time.time()
        user_message = await ChatMessageCRUD.create_message_async(
            db=self.db,
            session_id=session_id,
            user_id=user.id,
            content=payload.content,
            role="user",
            model_name=payload.model_name,
        )
        logger.debug(
            "保存用户消息完成: session_id={}, user_id={}, msg_id={}, elapsed_ms={}",
            session_id,
            user.id,
            user_message.id,
            int((time.time() - save_time) * 1000),
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
        save_ai_time = time.time()
        ai_message = await ChatMessageCRUD.create_message_async(
            db=self.db,
            session_id=session_id,
            user_id=user.id,
            content=ai_response,
            role="assistant",
            model_name="DeepSeek-V3.2",
        )

        total_elapsed = int((time.time() - start_time) * 1000)
        logger.info(
            "发送消息成功: session_id={}, user_id={}, user_msg_id={}, ai_msg_id={}, "
            "total_elapsed_ms={}, llm_elapsed_ms={}, response_length={}",
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
        """发送消息（流式响应）- yield 每个 token"""
        start_time = time.time()

        # 权限检查
        session = await self._get_session(user, session_id)
        if not session:
            logger.warning(
                "发送消息失败：会话不存在或无权限 session_id={}, user_id={}",
                session_id,
                user.id,
            )
            yield "Error: 会话不存在或无权限"
            return

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
            user_message.id,
        )

        # 2. 流式调用 LLM，同时yield每个token
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

        # 3. 保存 AI 响应到数据库
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
                "total_elapsed_ms={}, llm_elapsed_ms={}, token_count={}, response_length={}",
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
        """获取消息历史（分页）- 从 MySQL"""
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
        """获取会话（权限检查）"""
        if user.role == "admin":
            return await ChatSessionCRUD.get_session_by_id_async(self.db, session_id)
        else:
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
        """生成 AI 响应（整合 RAG）- 同步版本"""
        # 获取依赖服务
        llm_service = self._get_llm_service()
        redis_memory = self._get_redis_memory(session_id)
        markdown_memory = self._get_markdown_memory()

        # 从 MySQL 加载历史到 Redis（如果需要）
        await redis_memory.load_from_mysql(self.db)

        # 获取对话历史
        history = await redis_memory.get_context_for_llm(limit=10)

        # RAG 检索
        context = ""
        if file_id:
            try:
                rag_service = await self._get_rag_service()
                if rag_service is None:
                    logger.warning("RAG 服务不可用，跳过检索")
                else:
                    from app.services.rag.schemas import RagQuery

                    rag_result = await rag_service.search(
                        RagQuery(
                            text=user_message,
                            session_id=session_id,
                            filters={"file_id": int(file_id)}
                            if file_id.isdigit()
                            else None,
                            top_k=3,
                        )
                    )

                    if rag_result.hits:
                        context = "\n\n".join(
                            [
                                f"【来源 {i + 1}】{hit.content}"
                                for i, hit in enumerate(rag_result.hits)
                            ]
                        )
                    logger.info("RAG 检索到 {} 条结果", len(rag_result.hits))
            except Exception as e:
                logger.warning("RAG 检索失败: {}", e)

        # 获取 Markdown 长期记忆
        try:
            long_term_memory = await markdown_memory.load_memory(user_id, session_id)
        except Exception as e:
            logger.warning("加载长期记忆失败: {}", e)
            long_term_memory = ""

        # 构建 Prompt
        prompt_messages = self._build_prompt(
            user_message=user_message,
            context=context,
            history=history,
            long_term_memory=long_term_memory,
        )

        # 调用 LLM
        response = await llm_service.chat(prompt_messages)

        # 更新 Redis 记忆
        await redis_memory.append_message("user", user_message)
        await redis_memory.append_message("assistant", response)

        # 异步更新 Markdown 记忆（不阻塞响应）
        # 使用 asyncio.TaskGroup 或 ensure_future 来捕获异常
        task = asyncio.create_task(
            markdown_memory.append(user_id, session_id, user_message, response)
        )
        task.add_done_callback(
            lambda t: logger.error(f"Markdown 记忆更新失败: {t.exception()}")
            if not t.exception() is None
            else None
        )

        return response

    async def _generate_ai_response_stream(
            self,
            user_id: int,
            session_id: int,
            user_message: str,
            file_id: str | None,
    ) -> AsyncGenerator[str, None]:
        """生成 AI 响应（流式）- async generator"""
        # 获取依赖服务
        llm_service = self._get_llm_service()
        redis_memory = self._get_redis_memory(session_id)
        markdown_memory = self._get_markdown_memory()

        # 从 MySQL 加载历史到 Redis（如果需要）
        await redis_memory.load_from_mysql(self.db)

        # 获取对话历史, 默认只获取10条历史（在 RedisChatMemory 中配置）
        history = await redis_memory.get_context_for_llm()

        # RAG 检索
        context = ""
        if file_id:
            try:
                rag_service = await self._get_rag_service() # NOTE: 这里代码有问题
                if rag_service is None:
                    logger.warning("RAG 服务不可用，跳过检索")
                else:
                    from app.services.rag.schemas import RagQuery

                    rag_result: RagResult = await rag_service.search(
                        RagQuery(
                            text=user_message,
                            session_id=session_id,
                            filters={"file_id": int(file_id)}
                            if file_id.isdigit()
                            else None,
                            top_k=3,
                        )
                    )

                    if rag_result.hits:
                        context = "\n\n".join(
                            [
                                f"【来源 {i + 1}】{hit.content}"
                                for i, hit in enumerate(rag_result.hits)
                            ]
                        )
                        logger.info("RAG 检索到 {} 条结果", len(rag_result.hits))
            except Exception as e:
                logger.warning("RAG 检索失败: {}", e)

        # 获取 Markdown 长期记忆
        try:
            long_term_memory = await markdown_memory.load_memory(user_id, session_id)
        except Exception as e:
            logger.warning("加载长期记忆失败: {}", e)
            long_term_memory = ""

        # 构建 Prompt
        prompt_messages = self._build_prompt(
            user_message=user_message,
            context=context,
            history=history,
            long_term_memory=long_term_memory,
        )

        # 流式调用 LLM
        full_response = ""
        async for token in llm_service.chat_stream(prompt_messages):
            full_response += token
            yield token

        # 更新 Redis 记忆
        await redis_memory.append_message("user", user_message)
        await redis_memory.append_message("assistant", full_response)

        # 异步更新 Markdown 记忆（不阻塞响应）
        # 使用 add_done_callback 捕获异常
        task = asyncio.create_task(
            markdown_memory.append(user_id, session_id, user_message, full_response)
        )
        task.add_done_callback(
            lambda t: logger.error(f"Markdown 记忆更新失败: {t.exception()}")
            if not t.exception() is None
            else None
        )

    def _build_prompt(
            self,
            user_message: str,
            context: str,
            history: list[dict],
            long_term_memory: str,
    ) -> list[dict]:
        """构建 LLM 提示词"""
        # 构建历史对话字符串
        history_str = ""
        if history:
            for msg in history:
                role = "用户" if msg["role"] == "user" else "AI"
                history_str += f"{role}: {msg['content']}\n\n"

        # 填充模板
        prompt_text = RAG_PROMPT_TEMPLATE.format(
            context=context or "（无检索结果）",  # NOTE: context 为 RAG 检索结果
            history=history_str or "（无历史对话）",
            question=user_message,
        )

        # 添加长期记忆作为参考 NOTE: 这部分内容较长，放在最后，供 LLM 参考，不作为主要上下文. 这里还可以优化，比如只添加最近的部分记忆，或者添加记忆摘要等
        if long_term_memory:
            prompt_text += f"\n\n---\n\n# 历史摘要\n\n{long_term_memory}"

        return [
            {
                "role": "system",
                "content": "你是一个专业的AI助手，请根据提供的知识库和对话历史来回答用户的问题。",
            },
            {"role": "user", "content": prompt_text},
        ]
