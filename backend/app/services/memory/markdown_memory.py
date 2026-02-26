from __future__ import annotations

import io
import json
from datetime import datetime

from minio import Minio

from app.core.logging import get_logger
from app.core.settings import get_settings

logger = get_logger(__name__)

MEMORY_OBJECT_PREFIX = "memories/"


class MarkdownMemoryService:
    """Markdown 长期记忆服务 - 仅记录摘要信息，不记录对话历史"""

    def __init__(self, minio_client: Minio) -> None:
        settings = get_settings()
        self.minio = minio_client
        self.bucket = settings.MEMORY_BUCKET
        self.max_memory_chars = settings.MEMORY_MAX_CHARS

    def _get_object_name(self, user_id: int, session_id: int) -> str:
        return f"{MEMORY_OBJECT_PREFIX}user_{user_id}/session_{session_id}.md"

    async def load_memory(self, user_id: int, session_id: int) -> str:
        """从 MinIO 加载长期记忆"""
        object_name = self._get_object_name(user_id, session_id)

        try:
            response = self.minio.get_object(self.bucket, object_name)
            data = response.read().decode("utf-8")
            response.close()
            response.release_conn()
            logger.debug(
                "加载长期记忆: user_id={}, session_id={}, length={}",
                user_id,
                session_id,
                len(data),
            )
            return self._extract_memory_content(data)
        except Exception as e:
            logger.debug(
                "长期记忆不存在: user_id={}, session_id={}, error={}",
                user_id,
                session_id,
                e,
            )
            return ""

    def _extract_memory_content(self, content: str) -> str:
        """从完整 markdown 文档中提取记忆内容（Role & Policies 之后的部分）"""
        lines = content.split("\n")
        result = []
        capture = False

        for line in lines:
            if line.strip().startswith("# Role & Policies"):
                capture = True
            if capture:
                result.append(line)

        return "\n".join(result).strip()

    async def append_summary(
            self, user_id: int, session_id: int, user_message: str, ai_response: str
    ) -> None:
        """追加新对话摘要到长期记忆"""
        current_memory = await self.load_memory(user_id, session_id)

        new_summary = self._create_summary_entry(user_message, ai_response)

        updated_memory = (
            current_memory + "\n\n" + new_summary if current_memory else new_summary
        )

        # TODO: 目前的 markdown 结构中内容填写还有错误。
        updated_memory = self._ensure_header(updated_memory)

        # TODO：目前的截断策略比较简单，直接从头部开始截断；后续可以改进为更智能的方式，比如保留最近的 N 条摘要等
        updated_memory = self._truncate_if_needed(updated_memory)

        await self._save_memory(user_id, session_id, updated_memory)

    def _create_summary_entry(self, user_message: str, ai_response: str) -> str:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"""### {timestamp}

**用户**: {self._escape_markdown(user_message)}

**AI摘要**: {self._escape_markdown(ai_response[:200])}..."""

    def _escape_markdown(self, text: str) -> str:
        """转义 markdown 特殊字符"""
        if not text:
            return ""
        text = text.replace("```", "``````")
        text = text.replace("#", "\\#")
        text = text.replace("*", "\\*")
        text = text.replace("_", "\\_")
        text = text.replace("[", "\\[")
        text = text.replace("]", "\\]")
        text = text.replace("(", "\\(")
        text = text.replace(")", "\\)")
        return text

    def _ensure_header(self, content: str) -> str:
        """确保文档有正确的标题结构"""
        if not content.startswith("# Role & Policies"):
            header = """# Role & Policies

你是一个专业的AI助手。

# Task

回答用户问题。

# State

暂无

# Evidence

暂无

# Output

直接输出回答内容。

---

"""
            return header + content
        return content

    async def _save_memory(self, user_id: int, session_id: int, content: str) -> None:
        object_name = self._get_object_name(user_id, session_id)

        try:
            data = content.encode("utf-8")
            data_size = len(data)

            self.minio.put_object(
                self.bucket,
                object_name,
                io.BytesIO(data),
                data_size,
                content_type="text/markdown",
            )
            logger.info(
                "保存长期记忆成功: user_id={}, session_id={}, length={}",
                user_id,
                session_id,
                len(content),
            )
        except Exception as e:
            logger.error(
                "保存长期记忆失败: user_id={}, session_id={}, error={}",
                user_id,
                session_id,
                e,
            )
            raise

    def _truncate_if_needed(self, content: str) -> str:
        """如果内容过长，截断旧内容"""
        if len(content) <= self.max_memory_chars:
            return content

        lines = content.split("\n")
        result_lines = []
        current_chars = 0

        for line in reversed(lines):
            if current_chars + len(line) > self.max_memory_chars:
                break
            result_lines.insert(0, line)
            current_chars += len(line)

        return "\n".join(result_lines)
