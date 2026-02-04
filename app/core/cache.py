"""Simple in-memory cache with TTL for frequently accessed data."""
from datetime import datetime, timedelta
from typing import Any, Optional
import asyncio
from functools import wraps


class CacheEntry:
    """Cache entry with expiration."""
    def __init__(self, value: Any, ttl_seconds: int):
        self.value = value
        self.expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)

    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at


class SimpleCache:
    """Thread-safe in-memory cache with TTL."""

    def __init__(self):
        self._cache: dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        async with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None

            if entry.is_expired():
                del self._cache[key]
                return None

            return entry.value

    async def set(self, key: str, value: Any, ttl_seconds: int = 300):
        """Set value in cache with TTL (default 5 minutes)."""
        async with self._lock:
            self._cache[key] = CacheEntry(value, ttl_seconds)

    async def delete(self, key: str):
        """Delete key from cache."""
        async with self._lock:
            self._cache.pop(key, None)

    async def clear(self):
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()

    async def cleanup_expired(self):
        """Remove expired entries."""
        async with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]
            for key in expired_keys:
                del self._cache[key]


# Global cache instance
_cache = SimpleCache()


def cached(ttl_seconds: int = 300, key_prefix: str = ""):
    """
    Decorator for caching async function results.

    Usage:
        @cached(ttl_seconds=300, key_prefix="surveys")
        async def list_surveys(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Build cache key from function name and arguments
            cache_key = f"{key_prefix}:{func.__name__}:{str(args)}:{str(kwargs)}"

            # Try to get from cache
            cached_value = await _cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Call function and cache result
            result = await func(*args, **kwargs)
            await _cache.set(cache_key, result, ttl_seconds)

            return result

        return wrapper
    return decorator


async def invalidate_cache(pattern: str = ""):
    """Invalidate cache entries matching pattern."""
    if pattern:
        # For simplicity, clear all if pattern specified
        # In production, use Redis with pattern matching
        await _cache.clear()
    else:
        await _cache.clear()
