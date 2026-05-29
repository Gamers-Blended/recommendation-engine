import logging
import pickle
from typing import Any, Optional

import redis.asyncio as aioredis

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Module-level client - 1 connection pool shared across all requests
# redis.asyncio manages pool internally
_redis: aioredis.Redis | None = None


async def connect_cache() -> None:
    """Called  on app startup to initialize the Redis client."""
    global _redis
    settings = get_settings()
    _redis = aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=False, # Store binary (pickle), not plain strings
        max_connections=10, # Limit max connections in pool
    )

    # Verify connection immediately so startup fails fast on misconfiguration
    await _redis.ping()
    logger.info("Connected to Redis cache at %s", settings.redis_url)

    
async def close_cache() -> None:
    """Called on app shutdown to close the Redis client."""
    global _redis
    if _redis:
        await _redis.close()
        logger.info("Closed Redis cache connection")
        _redis = None


def _client() -> aioredis.Redis:
    """Helper to get the Redis client, ensuring it's initialised."""
    if _redis is None:
        raise RuntimeError("Redis client not initialised. connect_cache() was not awaited.")
    return _redis


class RedisCache:
    """
    Thin async wrapper around Redis with pickle serialisation.

    Pickle is used instead of JSON as values contain Pydantic models with Decimal fields, which are not JSON serialisable by default.
    """

    async def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache by key. Returns None if key is not found."""
        try:
            data = await _client().get(key)
            if data is None:
                return None
            return pickle.loads(data)
        except Exception as e:
            logger.warning("Cache GET failed for key = %s: %s", key, e, exc_info=True)
            return None
        
    async def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        """Set a value in the cache with a TTL."""
        try:
            await _client().setex(key, ttl_seconds, pickle.dumps(value))
        except Exception as e:
            logger.warning("Cache SET failed for key = %s: %s", key, e, exc_info=True)

    async def delete(self, key: str) -> None:
        """Delete a key from the cache."""
        try:
            await _client().delete(key)
        except Exception as e:
            logger.warning("Cache DELETE failed for key = %s: %s", key, e, exc_info=True)

    async def clear(self) -> None:
        """
        Flushes ALL keys in the current Redis database
        """
        try:
            await _client().flushdb()
        except Exception as e:
            logger.warning("Cache CLEAR failed: %s", e, exc_info=True)

# Single shared cache instance used across the app
cache = RedisCache()