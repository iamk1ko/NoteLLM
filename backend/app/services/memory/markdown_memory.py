from __future__ import annotations

import io
from datetime import datetime

from minio import Minio

from app.core.logging import get_logger
from app.core.settings import get_settings

logger = get_logger(__name__)

# Markdown 记忆文件路径前缀
MEMORY_OBJECT_PREFIX = "memories/"


class MarkdownMemoryService:
    """Markdown 记忆服务 - 长期记忆存储到 MinIO"""

    def __init__(self, minio_client: Minio) -> None:
        settings = get_settings()
        self.minio = minio_client
        self.bucket = settings.MEMORY_BUCKET
        self.max_memory_chars = settings.MEMORY_MAX_CHARS

    def _get_object_name(self, user_id: int, session_id: int) -> str:
        """获取记忆文件的对象名（区分用户和会话）"""
        return f"{MEMORY_OBJECT_PREFIX}user_{user_id}/session_{session_id}.md"

    async def load_memory(self, user_id: int, session_id: int) -> str:
        """从 MinIO 加载对话记忆"""
        object_name = self._get_object_name(user_id, session_id)

        try:
            response = self.minio.get_object(self.bucket, object_name)
            data = response.read().decode("utf-8")
            response.close()
            response.release_conn()
            logger.debug(
                "加载对话记忆: user_id={}, session_id={}, length={}",
                user_id,
                session_id,
                len(data),
            )
            return data
        except Exception as e:
            # 文件不存在，返回空
            logger.debug(
                "对话记忆不存在: user_id={}, session_id={}, error={}",
                user_id,
                session_id,
                e,
            )
            return self._create_initial_memory(user_id, session_id)

    async def save_memory(self, user_id: int, session_id: int, content: str) -> None:
        """保存对话记忆到 MinIO"""
        object_name = self._get_object_name(user_id, session_id)

        # 确保内容不超过最大长度
        content = self._truncate_if_needed(content)

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
                "保存对话记忆成功: user_id={}, session_id={}, length={}",
                user_id,
                session_id,
                len(content),
            )
        except Exception as e:
            logger.error(
                "保存对话记忆失败: user_id={}, session_id={}, error={}",
                user_id,
                session_id,
                e,
            )
            raise

    async def append(
        self, user_id: int, session_id: int, user_message: str, ai_response: str
    ) -> None:
        """追加新对话到记忆（读-改-写）"""
        # 先加载现有记忆
        current_memory = await self.load_memory(user_id, session_id)

        # 构建新的对话片段
        new_entry = self._format_message_pair(user_message, ai_response)

        # 追加新内容
        updated_memory = current_memory + "\n\n" + new_entry

        # 保存
        await self.save_memory(user_id, session_id, updated_memory)

    def _create_initial_memory(self, user_id: int, session_id: int) -> str:
        """创建初始记忆文件"""
        return f"""# 对话记忆

**用户 ID**: {user_id}
**会话 ID**: {session_id}
**创建时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

## 对话记录

"""

    def _format_message_pair(self, user_message: str, ai_response: str) -> str:
        """格式化一对对话为 Markdown"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"""### {timestamp}

**用户**: {user_message}

**AI**: {ai_response}"""

    def _truncate_if_needed(self, content: str) -> str:
        """如果内容过长，截断旧内容"""
        if len(content) <= self.max_memory_chars:
            return content

        # 找到 "---" 分隔符，保留后面的内容
        parts = content.split("---")
        if len(parts) >= 2:
            # 保留第一部分（头部）+ 第二部分的后半部分
            header = parts[0] + "---"
            body = "---".join(parts[1:])

            # 递归截断 body
            truncated_body = self._truncate_body(body)
            return header + truncated_body

        # 如果没有分隔符，直接截断
        return content[-self.max_memory_chars :]

    def _truncate_body(self, body: str) -> str:
        """截断对话记录主体"""
        if len(body) <= self.max_memory_chars:
            return body

        # 找到最后一个 "### " （对话分隔符）
        # 保留最近的内容
        lines = body.split("\n")
        result_lines = []
        current_chars = 0

        for line in reversed(lines):
            if current_chars + len(line) > self.max_memory_chars:
                break
            result_lines.insert(0, line)
            current_chars += len(line)

        return "\n".join(result_lines)
