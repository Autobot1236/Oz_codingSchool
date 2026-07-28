from redis.asyncio import Redis

from app.core.config import settings


_redis_client: Redis | None = None


def get_redis_client() -> Redis:
    """Return the process-wide asynchronous Redis client."""
    global _redis_client

    if _redis_client is None:
        _redis_client = Redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def close_redis_client() -> None:
    """Close the Redis connection pool during application shutdown."""
    global _redis_client

    if _redis_client is None:
        return

    await _redis_client.aclose()
    _redis_client = None
