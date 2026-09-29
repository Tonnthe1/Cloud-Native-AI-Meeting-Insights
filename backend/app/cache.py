"""
Redis read-through cache for meeting list/search responses.

Invalidation uses a generation counter instead of deleting keys: every cache
key embeds the current generation, and bumping it (a single INCR) makes all
previously cached entries unreachable; they then expire via their TTL. This
lets the worker, which only has a synchronous Redis client, invalidate
caches cheaply and avoids scanning the keyspace.
"""

import hashlib
import json
import logging
from typing import Any, Callable, Optional

import redis
from fastapi import Request
from fastapi.encoders import jsonable_encoder

logger = logging.getLogger(__name__)

MEETINGS_GENERATION_KEY = "cache:meetings:generation"


class CacheService:
    def __init__(self, redis_client: redis.Redis, default_ttl: int = 60):
        self.redis = redis_client
        self.default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache (None on miss or Redis error)."""
        try:
            cached_value = self.redis.get(key)
            if cached_value is not None:
                return json.loads(cached_value)
        except Exception as e:
            logger.warning(f"Cache get error for key {key}: {e}")
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Store a JSON-serializable value with a TTL."""
        try:
            self.redis.setex(key, ttl or self.default_ttl, json.dumps(value))
            return True
        except Exception as e:
            logger.warning(f"Cache set error for key {key}: {e}")
            return False

    def get_or_set(self, key: str, loader: Callable[[], Any],
                   ttl: Optional[int] = None) -> Any:
        """Return the cached value for key, computing it with loader on a
        miss. Values are stored JSON-encoded, so Pydantic models come back
        as plain dicts."""
        cached = self.get(key)
        if cached is not None:
            logger.debug(f"Cache hit for key: {key}")
            return cached
        value = jsonable_encoder(loader())
        self.set(key, value, ttl)
        return value

    def meetings_generation(self) -> str:
        try:
            return self.redis.get(MEETINGS_GENERATION_KEY) or "0"
        except Exception as e:
            logger.warning(f"Cache generation lookup failed: {e}")
            return "0"

    def meetings_key(self, request: Request) -> str:
        """Cache key for a meetings endpoint, based on path and query."""
        query = str(sorted(request.query_params.items()))
        digest = hashlib.md5(query.encode()).hexdigest()
        return (f"api:{request.url.path}:"
                f"g{self.meetings_generation()}:{digest}")

    def invalidate_meetings(self) -> None:
        invalidate_meeting_caches(self.redis)


def invalidate_meeting_caches(redis_client: redis.Redis) -> None:
    """Invalidate all cached meeting list/search responses."""
    try:
        redis_client.incr(MEETINGS_GENERATION_KEY)
    except Exception as e:
        logger.warning(f"Cache invalidation failed: {e}")
