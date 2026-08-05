"""Async Redis response caching with explicit namespace invalidation."""

import hashlib
import json
import logging
from functools import wraps
from typing import Any, Optional

import redis.asyncio as redis
from fastapi import Request

logger = logging.getLogger(__name__)


class CacheService:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.default_ttl = 60

    async def get(self, key: str) -> Optional[Any]:
        try:
            cached_value = await self.redis.get(key)
            return json.loads(cached_value) if cached_value else None
        except Exception as exc:
            logger.warning("Cache get failed for %s: %s", key, exc)
            return None

    async def set(self, key: str, value: Any,
                  ttl: Optional[int] = None) -> bool:
        try:
            serialized = json.dumps(value, default=str)
            await self.redis.setex(key, ttl or self.default_ttl, serialized)
            return True
        except Exception as exc:
            logger.warning("Cache set failed for %s: %s", key, exc)
            return False

    async def delete_pattern(self, pattern: str) -> int:
        deleted = 0
        try:
            async for key in self.redis.scan_iter(match=pattern, count=100):
                deleted += await self.redis.delete(key)
        except Exception as exc:
            logger.warning("Cache invalidation failed for %s: %s", pattern, exc)
        return deleted


def cache_key_for_request(request: Request, prefix: str = "api") -> str:
    query = "&".join(
        f"{key}={value}" for key, value in sorted(request.query_params.items())
    )
    digest = hashlib.sha256(query.encode()).hexdigest()[:16]
    return f"{prefix}:{request.url.path}:{digest}"


def cached_endpoint(ttl: int = 60, key_prefix: str = "api"):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = next(
                (value for value in (*args, *kwargs.values())
                 if isinstance(value, Request)),
                None,
            )
            cache_service = next(
                (value for value in kwargs.values()
                 if isinstance(value, CacheService)),
                None,
            )
            if request is None or cache_service is None:
                return await func(*args, **kwargs)

            cache_key = cache_key_for_request(request, key_prefix)
            cached_result = await cache_service.get(cache_key)
            if cached_result is not None:
                return cached_result

            result = await func(*args, **kwargs)
            await cache_service.set(cache_key, result, ttl)
            return result

        return wrapper
    return decorator


async def invalidate_meeting_caches(cache_service: CacheService) -> int:
    deleted = 0
    for pattern in ("api:/meetings:*", "api:/search:*"):
        deleted += await cache_service.delete_pattern(pattern)
    return deleted
