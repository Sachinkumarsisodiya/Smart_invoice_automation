import os
import redis
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.config import settings
from app.core.logging import logger


def get_limiter_storage_uri() -> str:
    """
    Dynamically resolves rate limiter backend.
    In production with active Redis, uses Redis URL.
    Falls back gracefully to fast in-memory storage during tests or when Redis is offline.
    """
    if os.getenv("PYTEST_CURRENT_TEST") or settings.APP_ENV in ("test", "testing") or not settings.REDIS_URL:
        return "memory://"

    try:
        r = redis.from_url(settings.REDIS_URL, socket_timeout=1)
        r.ping()
        return settings.REDIS_URL
    except Exception as e:
        logger.warning(f"Redis unavailable for rate limiter ({e}); falling back to memory://")
        return "memory://"


def is_rate_limit_exempt() -> bool:
    return bool(os.getenv("PYTEST_CURRENT_TEST") or settings.APP_ENV in ("test", "testing"))


limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=get_limiter_storage_uri(),
    headers_enabled=False,
    enabled=not is_rate_limit_exempt()
)
