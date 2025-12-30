import hashlib
import json
import time
from typing import Optional, Any
from functools import wraps
import logging

logger = logging.getLogger(__name__)


class CacheBackend:
    """Abstract cache backend interface."""
    
    def get(self, key: str) -> Optional[Any]:
        raise NotImplementedError
    
    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        raise NotImplementedError
    
    def delete(self, key: str) -> None:
        raise NotImplementedError
    
    def clear(self) -> None:
        raise NotImplementedError


class InMemoryCache(CacheBackend):
    """In-memory cache with TTL support."""
    
    def __init__(self):
        self._cache = {}
        self._expiry = {}
    
    def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            if time.time() < self._expiry.get(key, 0):
                return self._cache[key]
            else:
                self.delete(key)
        return None
    
    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        self._cache[key] = value
        self._expiry[key] = time.time() + ttl
    
    def delete(self, key: str) -> None:
        self._cache.pop(key, None)
        self._expiry.pop(key, None)
    
    def clear(self) -> None:
        self._cache.clear()
        self._expiry.clear()


class RedisCache(CacheBackend):
    """Redis cache backend."""
    
    def __init__(self, redis_url: str):
        try:
            import redis
            self._client = redis.from_url(redis_url)
            self._client.ping()
            logger.info("Redis cache connected")
        except Exception as e:
            logger.warning(f"Redis unavailable, falling back to in-memory: {e}")
            self._client = None
            self._fallback = InMemoryCache()
    
    def get(self, key: str) -> Optional[Any]:
        if self._client is None:
            return self._fallback.get(key)
        try:
            data = self._client.get(key)
            if data:
                return json.loads(data)
        except Exception:
            pass
        return None
    
    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        if self._client is None:
            self._fallback.set(key, value, ttl)
            return
        try:
            self._client.setex(key, ttl, json.dumps(value))
        except Exception:
            pass
    
    def delete(self, key: str) -> None:
        if self._client is None:
            self._fallback.delete(key)
            return
        try:
            self._client.delete(key)
        except Exception:
            pass
    
    def clear(self) -> None:
        if self._client is None:
            self._fallback.clear()
            return
        try:
            self._client.flushdb()
        except Exception:
            pass


class CacheManager:
    """Singleton cache manager."""
    
    _instance = None
    _cache: CacheBackend = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def initialize(self, redis_url: Optional[str] = None):
        if redis_url:
            self._cache = RedisCache(redis_url)
        else:
            self._cache = InMemoryCache()
            logger.info("Using in-memory cache")
    
    @property
    def cache(self) -> CacheBackend:
        if self._cache is None:
            self._cache = InMemoryCache()
        return self._cache


cache_manager = CacheManager()


def generate_cache_key(*args, **kwargs) -> str:
    """Generate cache key from arguments."""
    key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
    return hashlib.md5(key_data.encode()).hexdigest()


def cached(ttl: int = 300, prefix: str = ""):
    """Decorator for caching function results."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"{prefix}:{func.__name__}:{generate_cache_key(*args, **kwargs)}"
            
            cached_result = cache_manager.cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_result
            
            result = func(*args, **kwargs)
            cache_manager.cache.set(cache_key, result, ttl)
            logger.debug(f"Cache set: {cache_key}")
            return result
        return wrapper
    return decorator

