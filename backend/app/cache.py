"""
Redis caching service for high-performance API responses
"""

import json
import hashlib
import logging
from typing import Any, Optional, List, Dict
from functools import wraps
import asyncio

import redis.asyncio as redis
from fastapi import Request

logger = logging.getLogger(__name__)

class CacheService:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.default_ttl = 60  # 60 seconds default TTL
        
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            cached_value = await self.redis.get(key)
            if cached_value:
                return json.loads(cached_value)
        except Exception as e:
            logger.warning(f"Cache get error for key {key}: {e}")
        return None
    
    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set value in cache with TTL."""
        try:
            ttl = ttl or self.default_ttl
            serialized_value = json.dumps(value, default=str)
            await self.redis.setex(key, ttl, serialized_value)
            return True
        except Exception as e:
            logger.warning(f"Cache set error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Cache delete error for key {key}: {e}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern."""
        try:
            keys = await self.redis.keys(pattern)
            if keys:
                return await self.redis.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"Cache delete pattern error for {pattern}: {e}")
            return 0

def cache_key_for_request(request: Request, prefix: str = "") -> str:
    """Generate cache key for request based on path and query params."""
    path = request.url.path
    query_params = str(sorted(request.query_params.items()))
    key_string = f"{prefix}:{path}:{query_params}"
    return hashlib.md5(key_string.encode()).hexdigest()

def cached_endpoint(ttl: int = 60, key_prefix: str = "api"):
    """Decorator for caching API endpoint responses."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from kwargs (FastAPI dependency injection)
            request = None
            cache_service = None
            
            for arg in args:
                if hasattr(arg, 'url'):  # FastAPI Request object
                    request = arg
                    break
            
            for key, value in kwargs.items():
                if isinstance(value, CacheService):
                    cache_service = value
                    break
                elif hasattr(value, 'url'):  # Request in kwargs
                    request = value
            
            if not request or not cache_service:
                # If no cache service or request, just execute function
                return await func(*args, **kwargs)
            
            # Generate cache key
            cache_key = cache_key_for_request(request, key_prefix)
            
            # Try to get from cache
            cached_result = await cache_service.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for key: {cache_key}")
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            
            # Cache the result
            await cache_service.set(cache_key, result, ttl)
            logger.debug(f"Cache miss, stored result for key: {cache_key}")
            
            return result
            
        return wrapper
    return decorator

# Cache invalidation patterns
MEETING_CACHE_PATTERNS = [
    "api:/meetings*",
    "api:/search*"
]

async def invalidate_meeting_caches(cache_service: CacheService):
    """Invalidate all meeting-related caches."""
    for pattern in MEETING_CACHE_PATTERNS:
        deleted_count = await cache_service.delete_pattern(pattern)
        if deleted_count > 0:
            logger.info(f"Invalidated {deleted_count} cache entries for pattern: {pattern}")