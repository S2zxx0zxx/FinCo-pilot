from typing import Optional

import redis.asyncio as redis

from app.core.config import get_settings
from app.core.redis_runtime import create_async_redis_client

_redis: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        settings = get_settings()
        _redis = create_async_redis_client(
            settings.redis_url,
            max_connections=settings.redis_max_connections,
            socket_connect_timeout_seconds=settings.redis_socket_connect_timeout_seconds,
            socket_timeout_seconds=settings.redis_socket_timeout_seconds,
            health_check_interval_seconds=settings.redis_health_check_interval_seconds,
            ssl_ca_file=settings.redis_ssl_ca_file,
            client_name="fincopilot-api",
        )
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
