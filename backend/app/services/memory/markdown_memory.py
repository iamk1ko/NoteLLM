from __future__ import annotations

import io
import json

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
        """从 MinIO 加载长期记忆（全文）"""
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
            return data
        except Exception as e:
            logger.debug(
                "长期记忆不存在: user_id={}, session_id={}, error={}",
                user_id,
                session_id,
                e,
            )
            return ""

    async def apply_updates(
        self, user_id: int, session_id: int, updates: dict[str, str]
    ) -> None:
        """合并更新长期记忆内容"""
        current_memory = await self.load_memory(user_id, session_id)
        sections = self._parse_sections(current_memory)

        for key, value in updates.items():
            if value:
                sections[key] = self._sanitize_text(value)

        if not sections.get("role_policies"):
            sections["role_policies"] = "你是一个专业的AI助手。"
        if not sections.get("task"):
            sections["task"] = "回答用户问题。"
        if not sections.get("state"):
            sections["state"] = "暂无"
        if not sections.get("output"):
            sections["output"] = "直接输出回答内容。"

        updated_memory = self._render_sections(sections)
        updated_memory = self._truncate_if_needed(updated_memory)
        await self._save_memory(user_id, session_id, updated_memory)

    def _sanitize_text(self, text: str) -> str:
        if not text:
            return ""
        return text.replace("```", "").replace("#", "").strip()

    def _parse_sections(self, content: str) -> dict[str, str]:
        sections = {
            "role_policies": "",
            "task": "",
            "state": "",
            "output": "",
        }
        if not content:
            return sections

        current = ""
        for line in content.split("\n"):
            header = line.strip().lower()
            if header.startswith("# role"):
                current = "role_policies"
                continue
            if header.startswith("# task"):
                current = "task"
                continue
            if header.startswith("# state"):
                current = "state"
                continue
            if header.startswith("# output"):
                current = "output"
                continue
            if current:
                sections[current] += line + "\n"

        return {k: v.strip() for k, v in sections.items()}

    def _render_sections(self, sections: dict[str, str]) -> str:
        return (
            "# Role & Policies\n\n"
            f"{sections.get('role_policies', '')}\n\n"
            "# Task\n\n"
            f"{sections.get('task', '')}\n\n"
            "# State\n\n"
            f"{sections.get('state', '')}\n\n"
            "# Output\n\n"
            f"{sections.get('output', '')}\n"
        )

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
