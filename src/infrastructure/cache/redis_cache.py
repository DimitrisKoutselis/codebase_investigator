import json
from typing import Any, Optional

import redis.asyncio as redis

from src.application.interfaces.i_cache_service import ICacheService


class RedisCacheService(ICacheService):
    """Redis-based cache implementation."""

    def __init__(self, redis_url: str, default_ttl: int = 3600):
        self._redis_url = redis_url
        self._default_ttl = default_ttl
        self._client: redis.Redis | None = None

    async def _get_client(self) -> redis.Redis:
        """Get or create Redis client."""
        if self._client is None:
            self._client = redis.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._client

    async def get(self, key: str) -> Optional[Any]:
        """Get a value from cache."""
        client = await self._get_client()
        value = await client.get(key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int | None = None,
    ) -> None:
        """Set a value in cache with optional TTL."""
        client = await self._get_client()
        ttl = ttl_seconds or self._default_ttl

        if isinstance(value, (dict, list)):
            value = json.dumps(value)

        await client.set(key, value, ex=ttl)

    async def delete(self, key: str) -> None:
        """Delete a key from cache."""
        client = await self._get_client()
        await client.delete(key)

    async def exists(self, key: str) -> bool:
        """Check if a key exists in cache."""
        client = await self._get_client()
        return await client.exists(key) > 0

    async def clear_pattern(self, pattern: str) -> None:
        """Clear all keys matching a pattern."""
        client = await self._get_client()
        cursor = 0
        while True:
            cursor, keys = await client.scan(cursor, match=pattern)
            if keys:
                await client.delete(*keys)
            if cursor == 0:
                break

    async def close(self) -> None:
        """Close the Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None
