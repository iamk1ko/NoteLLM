from __future__ import annotations

from app.core.logging import get_logger
from app.core.settings import get_settings
from app.prompts import load_prompt

logger = get_logger(__name__)

SYSTEM_PROMPT = load_prompt("chat_system.txt")
USER_PROMPT_TEMPLATE = load_prompt("chat_user.txt")


class PromptBuilder:
    def build_prompt(
        self,
        user_message: str,
        evidence: str,
        history: list[dict],
        long_term_memory: str,
    ) -> list[dict]:
        """构建 LLM 输入的 prompt，整合用户消息、RAG 证据、历史对话和长期记忆"""
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
        logger.info("已成功构建完整 LLM Prompt。")

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
