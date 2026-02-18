"""
Caching Layer for Cell 0 OS

Provides comprehensive caching capabilities:
- Redis client wrapper with circuit breaker
- HTTP response caching
- Search result caching
- Model output semantic caching

Author: KULLU (Cell 0 OS)
"""

from cell0.engine.cache.redis_client import (
    RedisClient,
    RedisConfig,
    CircuitBreaker,
    CircuitBreakerOpen,
    get_redis_client,
    initialize_redis,
    close_redis,
)

from cell0.engine.cache.response_cache import (
    ResponseCache,
    CacheConfig,
    CacheStrategy,
    CachedResponse,
    cached,
    get_response_cache,
)

try:
    from cell0.engine.cache.response_cache import CacheMiddleware
except ImportError:
    CacheMiddleware = None

from cell0.engine.cache.search_cache import (
    SearchResultCache,
    SemanticSearchCache,
    SearchCacheEntry,
    SearchProvider,
    SearchType,
    get_search_cache,
    get_semantic_search_cache,
)

from cell0.engine.cache.model_output_cache import (
    ModelOutputCache,
    ModelOutputEntry,
    CacheMatch,
    CacheMatchConfidence,
    SimpleEmbeddingGenerator,
    with_model_cache,
    get_model_output_cache,
)

__all__ = [
    # Redis client
    "RedisClient",
    "RedisConfig",
    "CircuitBreaker",
    "CircuitBreakerOpen",
    "get_redis_client",
    "initialize_redis",
    "close_redis",
    
    # Response cache
    "ResponseCache",
    "CacheConfig",
    "CacheStrategy",
    "CachedResponse",
    "CacheMiddleware",
    "cached",
    "get_response_cache",
    
    # Search cache
    "SearchResultCache",
    "SemanticSearchCache",
    "SearchCacheEntry",
    "SearchProvider",
    "SearchType",
    "get_search_cache",
    "get_semantic_search_cache",
    
    # Model output cache
    "ModelOutputCache",
    "ModelOutputEntry",
    "CacheMatch",
    "CacheMatchConfidence",
    "SimpleEmbeddingGenerator",
    "with_model_cache",
    "get_model_output_cache",
]