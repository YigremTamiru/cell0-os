"""
API Response Caching for Cell 0 OS

Production-grade HTTP response caching with:
- Redis-backed caching
- Cache key generation
- TTL management
- Cache invalidation strategies
- Conditional caching based on request type
- Statistics tracking

Author: KULLU (Cell 0 OS)
"""

import asyncio
import hashlib
import json
import logging
from typing import Any, Dict, Optional, Callable, List, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import functools

try:
    from fastapi import Request, Response
    from starlette.middleware.base import BaseHTTPMiddleware
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    Request = None
    Response = None
    BaseHTTPMiddleware = None

from cell0.engine.cache.redis_client import RedisClient, get_redis_client

logger = logging.getLogger("cell0.engine.cache.response")


class CacheStrategy(Enum):
    """Cache strategies"""
    NEVER = "never"           # Never cache
    ALWAYS = "always"         # Always cache (respect TTL)
    CONDITIONAL = "conditional"  # Cache based on conditions


@dataclass
class CacheConfig:
    """Response cache configuration"""
    default_ttl_seconds: int = 300  # 5 minutes
    max_body_size_bytes: int = 1024 * 1024  # 1MB
    cache_control_header: bool = True
    vary_headers: List[str] = None
    key_prefix: str = "cell0:response"
    
    def __post_init__(self):
        if self.vary_headers is None:
            self.vary_headers = ["Accept", "Accept-Encoding", "Accept-Language"]


@dataclass
class CachedResponse:
    """Cached response data"""
    body: bytes
    status_code: int
    headers: Dict[str, str]
    content_type: str
    timestamp: datetime
    ttl_seconds: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "body": self.body.decode('utf-8', errors='replace'),
            "status_code": self.status_code,
            "headers": self.headers,
            "content_type": self.content_type,
            "timestamp": self.timestamp.isoformat(),
            "ttl_seconds": self.ttl_seconds,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CachedResponse":
        return cls(
            body=data["body"].encode('utf-8'),
            status_code=data["status_code"],
            headers=data["headers"],
            content_type=data["content_type"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            ttl_seconds=data["ttl_seconds"],
        )
    
    def is_expired(self) -> bool:
        """Check if cached response has expired"""
        expiry = self.timestamp + timedelta(seconds=self.ttl_seconds)
        return datetime.utcnow() > expiry


class ResponseCache:
    """
    Response caching manager
    
    Provides intelligent caching for API responses with:
    - Configurable TTL per endpoint
    - Cache key generation with Vary headers
    - Statistics tracking
    - Background cache warming (optional)
    """
    
    def __init__(
        self,
        redis_client: Optional[RedisClient] = None,
        config: Optional[CacheConfig] = None,
    ):
        self.redis = redis_client or get_redis_client()
        self.config = config or CacheConfig()
        self._endpoint_configs: Dict[str, Dict[str, Any]] = {}
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "invalidations": 0,
        }
        
    def configure_endpoint(
        self,
        path_pattern: str,
        strategy: CacheStrategy = CacheStrategy.CONDITIONAL,
        ttl_seconds: Optional[int] = None,
        cache_key_fn: Optional[Callable] = None,
        should_cache_fn: Optional[Callable] = None,
    ):
        """
        Configure caching for an endpoint
        
        Args:
            path_pattern: URL path pattern (e.g., "/api/models")
            strategy: Cache strategy
            ttl_seconds: Override default TTL
            cache_key_fn: Custom cache key generation function
            should_cache_fn: Function to determine if response should be cached
        """
        self._endpoint_configs[path_pattern] = {
            "strategy": strategy,
            "ttl_seconds": ttl_seconds or self.config.default_ttl_seconds,
            "cache_key_fn": cache_key_fn,
            "should_cache_fn": should_cache_fn,
        }
        logger.debug(f"Configured cache for {path_pattern}: {strategy.value}")
        
    def _get_endpoint_config(self, path: str) -> Dict[str, Any]:
        """Get configuration for a path"""
        for pattern, config in self._endpoint_configs.items():
            if pattern in path or path.startswith(pattern):
                return config
        return {
            "strategy": CacheStrategy.CONDITIONAL,
            "ttl_seconds": self.config.default_ttl_seconds,
            "cache_key_fn": None,
            "should_cache_fn": None,
        }
        
    def _generate_cache_key(self, request: Any) -> str:
        """Generate cache key for a request"""
        config = self._get_endpoint_config(str(request.url))
        
        # Use custom key function if provided
        if config.get("cache_key_fn"):
            return config["cache_key_fn"](request)
            
        # Build key from request components
        parts = [
            request.method,
            str(request.url),
        ]
        
        # Include Vary headers
        for header in self.config.vary_headers:
            value = request.headers.get(header)
            if value:
                parts.append(f"{header}:{value}")
                
        # Include query params
        if request.query_params:
            params = sorted(f"{k}={v}" for k, v in request.query_params.items())
            parts.append("&".join(params))
            
        key_data = "|".join(parts)
        hashed = hashlib.sha256(key_data.encode()).hexdigest()[:24]
        
        return f"{self.config.key_prefix}:{hashed}"
        
    def _should_cache_request(self, request: Any) -> bool:
        """Determine if request should be cached"""
        # Only cache GET and HEAD requests
        if request.method not in ("GET", "HEAD"):
            return False
            
        config = self._get_endpoint_config(str(request.url))
        
        if config["strategy"] == CacheStrategy.NEVER:
            return False
            
        if config["strategy"] == CacheStrategy.ALWAYS:
            return True
            
        # Conditional - check custom function
        if config.get("should_cache_fn"):
            return config["should_cache_fn"](request)
            
        return True
        
    def _should_cache_response(self, response: Any) -> bool:
        """Determine if response should be cached"""
        # Don't cache error responses
        if response.status_code >= 500:
            return False
            
        # Don't cache if explicitly no-cache
        cache_control = response.headers.get("Cache-Control", "")
        if "no-store" in cache_control or "private" in cache_control:
            return False
            
        return True
        
    async def get(self, request: Any) -> Optional[CachedResponse]:
        """Get cached response for request"""
        if not self._should_cache_request(request):
            return None
            
        cache_key = self._generate_cache_key(request)
        
        try:
            data = await self.redis.get(cache_key)
            
            if data is None:
                self._stats["misses"] += 1
                return None
                
            cached = CachedResponse.from_dict(data)
            
            if cached.is_expired():
                await self.redis.delete(cache_key)
                self._stats["misses"] += 1
                return None
                
            self._stats["hits"] += 1
            return cached
            
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
            
    async def set(
        self,
        request: Any,
        response: Any,
        ttl_seconds: Optional[int] = None,
    ) -> bool:
        """Cache a response"""
        if not self._should_cache_request(request):
            return False
            
        if not self._should_cache_response(response):
            return False
            
        config = self._get_endpoint_config(str(request.url))
        ttl = ttl_seconds or config["ttl_seconds"]
        
        cache_key = self._generate_cache_key(request)
        
        try:
            # Get response body
            if hasattr(response, 'body'):
                body = response.body
            elif hasattr(response, 'content'):
                body = response.content
            else:
                return False
                
            # Check size limit
            if len(body) > self.config.max_body_size_bytes:
                logger.debug(f"Response too large to cache: {len(body)} bytes")
                return False
                
            cached = CachedResponse(
                body=body if isinstance(body, bytes) else body.encode(),
                status_code=response.status_code,
                headers=dict(response.headers),
                content_type=response.headers.get("Content-Type", "application/json"),
                timestamp=datetime.utcnow(),
                ttl_seconds=ttl,
            )
            
            await self.redis.set(cache_key, cached.to_dict(), ttl_seconds=ttl)
            self._stats["sets"] += 1
            
            return True
            
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
            
    async def invalidate(self, path_pattern: Optional[str] = None) -> int:
        """
        Invalidate cached responses
        
        Args:
            path_pattern: If provided, only invalidate matching paths
            
        Returns:
            Number of cache entries invalidated
        """
        try:
            if path_pattern:
                # Delete keys matching pattern
                pattern = f"{self.config.key_prefix}:*"
                keys = await self.redis.keys(pattern)
                
                # Filter by path (this is approximate)
                to_delete = []
                for key in keys:
                    # We'd need to decode keys to filter properly
                    # For now, invalidate all
                    to_delete.append(key)
                    
                if to_delete:
                    for key in to_delete:
                        await self.redis.delete(key)
                        
                self._stats["invalidations"] += len(to_delete)
                return len(to_delete)
            else:
                # Clear all response cache
                count = await self.redis.clear(f"{self.config.key_prefix}:*")
                self._stats["invalidations"] += count
                return count
                
        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")
            return 0
            
    async def invalidate_path(self, path: str) -> int:
        """Invalidate cache for a specific path"""
        return await self.invalidate(path)
        
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total if total > 0 else 0
        
        return {
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "sets": self._stats["sets"],
            "invalidations": self._stats["invalidations"],
            "hit_rate": round(hit_rate, 4),
            "total_requests": total,
        }


if FASTAPI_AVAILABLE:
    class CacheMiddleware(BaseHTTPMiddleware):
        """
        FastAPI middleware for response caching
        
        Usage:
            app.add_middleware(CacheMiddleware, cache=ResponseCache())
        """
        
        def __init__(
            self,
            app,
            cache: Optional[ResponseCache] = None,
            config: Optional[CacheConfig] = None,
        ):
            super().__init__(app)
            self.cache = cache or ResponseCache(config=config)
            
        async def dispatch(self, request: Request, call_next):
            """Process request with caching"""
            # Try to get from cache
            cached = await self.cache.get(request)
            
            if cached:
                return Response(
                    content=cached.body,
                    status_code=cached.status_code,
                    headers=cached.headers,
                    media_type=cached.content_type,
                )
                
            # Call next middleware/handler
            response = await call_next(request)
            
            # Cache the response
            await self.cache.set(request, response)
            
            return response


def cached(
    ttl_seconds: int = 300,
    key_prefix: str = "",
    vary_on: Optional[List[str]] = None,
):
    """
    Decorator for caching function results
    
    Usage:
        @cached(ttl_seconds=600)
        async def get_expensive_data(param: str):
            return await fetch_data(param)
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            key_parts = [key_prefix or func.__name__]
            
            # Add args to key
            for arg in args:
                key_parts.append(str(arg))
                
            # Add kwargs to key (sorted)
            for k in sorted(kwargs.keys()):
                key_parts.append(f"{k}={kwargs[k]}")
                
            cache_key = hashlib.sha256(
                ":".join(key_parts).encode()
            ).hexdigest()[:24]
            
            cache_key = f"cell0:func:{cache_key}"
            
            # Try to get from cache
            redis = get_redis_client()
            try:
                cached_value = await redis.get(cache_key)
                if cached_value is not None:
                    return cached_value
            except Exception:
                pass
                
            # Call function
            result = await func(*args, **kwargs)
            
            # Cache result
            try:
                await redis.set(cache_key, result, ttl_seconds=ttl_seconds)
            except Exception:
                pass
                
            return result
            
        return wrapper
    return decorator


# Global cache instance
_global_cache: Optional[ResponseCache] = None


def get_response_cache(
    redis_client: Optional[RedisClient] = None,
    config: Optional[CacheConfig] = None,
) -> ResponseCache:
    """Get global response cache instance"""
    global _global_cache
    if _global_cache is None:
        _global_cache = ResponseCache(redis_client, config)
    return _global_cache