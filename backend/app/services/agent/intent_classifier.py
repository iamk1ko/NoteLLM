from __future__ import annotations

from dataclasses import dataclass

from app.core.logging import get_logger
from app.prompts import load_prompt
from app.services.llm.service import LLMService

logger = get_logger(__name__)

INTENT_PROMPT = load_prompt("intent_classifier.txt")


class IntentClassifier:
    def __init__(self, llm_service: LLMService) -> None:
        self.llm_service = llm_service

    async def classify(self, user_message: str) -> str:
        # 意图分类只允许输出单行 JSON，便于稳定解析
        prompt = f"{INTENT_PROMPT}\n\n用户：{user_message}\n输出："
        need_retrieval: str = await self.llm_service.chat_with_overrides(
            [
                {
                    "role": "system",
                    "content": "你是一个严格的JSON分类器，只输出单行JSON。",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
        )
        return need_retrieval
