from app.core.settings import get_settings
from app.services.llm.service import LLMService


def get_llm_service() -> LLMService:
    """获取 LLM 服务实例（同步）"""
    settings = get_settings()

    if not settings.BLSC_API_KEY or not settings.BLSC_BASE_URL:
        raise ValueError("LLM not configured: BLSC_API_KEY or BLSC_BASE_URL is missing")

    return LLMService(
        api_key=settings.BLSC_API_KEY,
        base_url=settings.BLSC_BASE_URL,
        model=settings.LLM_MODEL,
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
    )
