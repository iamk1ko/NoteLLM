from __future__ import annotations

import json
from dataclasses import dataclass

from app.core.logging import get_logger
from app.prompts import load_prompt
from app.services.llm.service import LLMService

logger = get_logger(__name__)

INTENT_PROMPT = load_prompt("intent_classifier.txt")


@dataclass(slots=True)  # slots 可以节省内存，适合大量实例的简单数据结构
class IntentResult:
    need_retrieval: str


class IntentClassifier:
    def __init__(self, llm_service: LLMService) -> None:
        self.llm_service = llm_service

    async def classify(self, user_message: str) -> IntentResult:
        # 意图分类只允许输出单行 JSON，便于稳定解析
        prompt = f"{INTENT_PROMPT}\n\n用户：{user_message}\n输出："
        raw = await self.llm_service.chat_with_overrides(
            [
                {
                    "role": "system",
                    "content": "你是一个严格的JSON分类器，只输出单行JSON。",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
        )
        parsed = self._parse_output(raw)
        return IntentResult(need_retrieval=parsed)

    @staticmethod
    def _parse_output(raw: str) -> str:
        text = (raw or "").strip()
        try:
            data = json.loads(text)
            value = str(data.get("need_retrieval", "")).strip().lower()
            if value in {"yes", "no"}:
                return value
        except Exception:
            # 解析失败按保守策略处理，避免漏检索
            logger.warning("意图分类输出解析失败，使用默认 yes: {}", text)
        return "yes"
