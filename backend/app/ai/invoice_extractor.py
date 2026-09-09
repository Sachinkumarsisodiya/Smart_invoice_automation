from app.config import settings
from app.ai.provider import BaseAIProvider
from app.ai.mock_provider import MockAIProvider
from app.ai.real_provider import RealAIProvider
from app.core.logging import logger


def get_ai_provider() -> BaseAIProvider:
    """Factory function returning the configured AI Provider."""
    provider_name = settings.AI_PROVIDER.lower().strip()
    if provider_name == "real":
        logger.info("[AI Factory] Selected RealAIProvider (LLM Mode)")
        return RealAIProvider()
    else:
        logger.info("[AI Factory] Selected MockAIProvider (Demo Mode)")
        return MockAIProvider()
