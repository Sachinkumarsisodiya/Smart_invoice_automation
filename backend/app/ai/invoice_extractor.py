import os
from app.config import settings
from app.ai.provider import BaseAIProvider
from app.ai.mock_provider import MockAIProvider
from app.ai.real_provider import RealAIProvider
from app.core.logging import logger


def get_ai_provider() -> BaseAIProvider:
    """Factory function returning the configured AI Provider."""
    api_key = (
        os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
        or os.getenv("AI_API_KEY")
        or settings.GEMINI_API_KEY
        or settings.AI_API_KEY
        or ""
    ).strip()
    provider_name = settings.AI_PROVIDER.lower().strip()
    
    if (provider_name in ("real", "gemini", "openai") and bool(api_key)) or bool(api_key):
        logger.info("[AI Factory] Selected RealAIProvider (Gemini / Vision Cloud AI Mode)")
        return RealAIProvider(api_key=api_key)
    else:
        logger.info("[AI Factory] Selected MockAIProvider (Deterministic Lightweight Mode)")
        return MockAIProvider()


