import os
from app.config import settings
from app.ai.provider import BaseAIProvider
from app.ai.mock_provider import MockAIProvider
from app.ai.real_provider import RealAIProvider
from app.core.logging import logger


def get_ai_provider() -> BaseAIProvider:
    """Factory function returning the configured AI Provider."""
    has_api_key = bool(os.getenv("GEMINI_API_KEY") or settings.AI_API_KEY)
    provider_name = settings.AI_PROVIDER.lower().strip()
    
    if provider_name == "real" or has_api_key:
        logger.info("[AI Factory] Selected RealAIProvider (Vision / LLM Mode)")
        return RealAIProvider()
    else:
        logger.info("[AI Factory] Selected MockAIProvider (Deterministic Mode)")
        return MockAIProvider()

