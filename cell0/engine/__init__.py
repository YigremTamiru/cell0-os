"""
Cell 0 OS - Core Engine
"""

# Security is always available
from . import security

# Monitoring (optional)
try:
    from . import monitoring
    from .monitoring import (
        get_logger,
        set_trace_id,
        trace_context,
        configure_logging,
        health_registry,
        metrics_handler,
    )
    _monitoring_available = True
except ImportError:
    _monitoring_available = False
    monitoring = None

# Resource Management (optional)
try:
    from .resource_limits import (
        ResourceMonitor,
        ResourceLimiter,
        ResourceLimits,
        ResourceUsage,
        ResourceAlert,
        ResourceType,
        ResourceAlertLevel,
        ModelMemoryManager,
        ModelInfo,
        EvictionPolicy,
        DiskCleanupManager,
        RequestResourceTracker,
        get_resource_monitor,
        get_resource_limiter,
        get_model_manager,
        get_disk_cleanup,
        get_request_tracker,
        initialize_resource_management,
        shutdown_resource_management,
    )
    _resource_limits_available = True
except ImportError:
    _resource_limits_available = False

# Performance (optional)
try:
    from .performance import (
        ConnectionPool,
        HTTPConnectionPool,
        RequestCoalescer,
        coalesced,
        AsyncBatchProcessor,
        TokenBucketRateLimiter,
        Memoizer,
        async_lru_cache,
        LazyLoader,
        get_http_pool,
        close_all_http_pools,
        get_request_coalescer,
    )
    _performance_available = True
except ImportError:
    _performance_available = False

# Caching Layer (optional)
try:
    from . import cache
    from .cache import (
        RedisClient,
        RedisConfig,
        CircuitBreaker,
        CircuitBreakerOpen,
        get_redis_client,
        initialize_redis,
        close_redis,
        ResponseCache,
        CacheConfig,
        CacheStrategy,
        CachedResponse,
        cached,
        get_response_cache,
        SearchResultCache,
        SemanticSearchCache,
        SearchCacheEntry,
        SearchProvider,
        SearchType,
        get_search_cache,
        get_semantic_search_cache,
        ModelOutputCache,
        ModelOutputEntry,
        CacheMatch,
        CacheMatchConfidence,
        SimpleEmbeddingGenerator,
        with_model_cache,
        get_model_output_cache,
    )
    _cache_available = True
except ImportError:
    _cache_available = False
    cache = None

# Error Handling (optional)
try:
    from .error_handling import (
        ErrorConfig,
        Cell0Exception,
        ErrorSeverity,
        ErrorCategory,
        ErrorContext,
        AuthenticationException,
        InvalidCredentialsException,
        TokenExpiredException,
        InsufficientPermissionsException,
        ValidationException,
        ResourceNotFoundException,
        ServiceUnavailableException,
        ExternalServiceException,
        OllamaException,
        SignalException,
        RateLimitException,
        TimeoutException,
        ConfigurationException,
        NetworkException,
        SentryManager,
        FallbackManager,
        ErrorHandler,
        get_sentry_manager,
        get_fallback_manager,
        get_error_handler,
        retry_with_backoff,
    )
    _error_handling_available = True
except ImportError:
    _error_handling_available = False

__all__ = [
    'security',
]

if _monitoring_available:
    __all__.extend([
        'monitoring',
        'get_logger',
        'set_trace_id',
        'trace_context',
        'configure_logging',
        'health_registry',
        'metrics_handler',
    ])

if _resource_limits_available:
    __all__.extend([
        'ResourceMonitor',
        'ResourceLimiter',
        'ResourceLimits',
        'ResourceUsage',
        'ResourceAlert',
        'ResourceType',
        'ResourceAlertLevel',
        'ModelMemoryManager',
        'ModelInfo',
        'EvictionPolicy',
        'DiskCleanupManager',
        'RequestResourceTracker',
        'get_resource_monitor',
        'get_resource_limiter',
        'get_model_manager',
        'get_disk_cleanup',
        'get_request_tracker',
        'initialize_resource_management',
        'shutdown_resource_management',
    ])

if _performance_available:
    __all__.extend([
        'ConnectionPool',
        'HTTPConnectionPool',
        'RequestCoalescer',
        'coalesced',
        'AsyncBatchProcessor',
        'TokenBucketRateLimiter',
        'Memoizer',
        'async_lru_cache',
        'LazyLoader',
        'get_http_pool',
        'close_all_http_pools',
        'get_request_coalescer',
    ])

if _cache_available:
    __all__.extend([
        'cache',
        'RedisClient',
        'RedisConfig',
        'CircuitBreaker',
        'CircuitBreakerOpen',
        'ResponseCache',
        'CacheConfig',
        'CacheStrategy',
        'CachedResponse',
        'cached',
        'SearchResultCache',
        'SemanticSearchCache',
        'ModelOutputCache',
        'CacheMatch',
        'CacheMatchConfidence',
    ])

if _error_handling_available:
    __all__.extend([
        'ErrorConfig',
        'Cell0Exception',
        'ErrorSeverity',
        'ErrorCategory',
        'ErrorContext',
        'AuthenticationException',
        'InvalidCredentialsException',
        'TokenExpiredException',
        'InsufficientPermissionsException',
        'ValidationException',
        'ResourceNotFoundException',
        'ServiceUnavailableException',
        'ExternalServiceException',
        'OllamaException',
        'SignalException',
        'RateLimitException',
        'TimeoutException',
        'ConfigurationException',
        'NetworkException',
        'SentryManager',
        'FallbackManager',
        'ErrorHandler',
        'get_sentry_manager',
        'get_fallback_manager',
        'get_error_handler',
        'retry_with_backoff',
    ])
