"""
cell0/engine/security/rate_limiter.py - Rate Limiting & Resource Protection

Production-ready rate limiting for Cell 0 OS:
- Per-IP and per-user rate limits
- Concurrent request limiting (Semaphore-based)
- Circuit breaker pattern for external services
- Token bucket algorithm
- Sliding window rate limiting
- Adaptive rate limiting based on system load
"""

import asyncio
import hashlib
import logging
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger("cell0.security.rate_limiter")


# ============================================================================
# Exceptions
# ============================================================================

class RateLimitExceeded(Exception):
    """Rate limit has been exceeded"""
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        limit: Optional[int] = None,
        window: Optional[int] = None,
    ):
        super().__init__(message)
        self.message = message
        self.retry_after = retry_after
        self.limit = limit
        self.window = window


class CircuitBreakerOpen(Exception):
    """Circuit breaker is open (service unavailable)"""
    def __init__(
        self,
        service: str,
        message: str = "Service temporarily unavailable",
        retry_after: Optional[int] = None,
    ):
        super().__init__(message)
        self.service = service
        self.message = message
        self.retry_after = retry_after


class ConcurrencyLimitExceeded(Exception):
    """Too many concurrent requests"""
    def __init__(self, message: str = "Server at capacity"):
        super().__init__(message)


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class RateLimitConfig:
    """Rate limit configuration"""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    requests_per_day: int = 10000
    burst_size: int = 10  # Allow burst of requests
    
    # Concurrent request limits
    max_concurrent_per_user: int = 10
    max_concurrent_global: int = 100
    
    # Adaptive settings
    enable_adaptive: bool = True
    high_load_threshold: float = 0.8  # 80% of max concurrent
    adaptive_reduction_factor: float = 0.5  # Reduce limits by 50% under high load


@dataclass
class RateLimitState:
    """Current rate limit state for a key"""
    key: str
    requests_in_window: int = 0
    window_start: float = field(default_factory=time.time)
    last_request: float = field(default_factory=time.time)
    tokens: float = 0  # For token bucket
    
    def reset_window(self, window_size: int):
        """Reset the window if expired"""
        now = time.time()
        if now - self.window_start >= window_size:
            self.requests_in_window = 0
            self.window_start = now


@dataclass
class CircuitBreakerState:
    """Circuit breaker state"""
    service: str
    failures: int = 0
    success_count: int = 0
    last_failure_time: Optional[float] = None
    state: str = "closed"  # closed, open, half_open
    opened_at: Optional[float] = None
    
    def record_success(self):
        """Record a successful call"""
        self.success_count += 1
        if self.state == "half_open" and self.success_count >= 3:
            self.state = "closed"
            self.failures = 0
            logger.info(f"Circuit breaker for {self.service} closed")
    
    def record_failure(self):
        """Record a failed call"""
        self.failures += 1
        self.last_failure_time = time.time()
        self.success_count = 0
        
        if self.state == "half_open":
            self.state = "open"
            self.opened_at = time.time()
            logger.warning(f"Circuit breaker for {self.service} opened (half-open failure)")
        elif self.failures >= 5 and self.state == "closed":
            self.state = "open"
            self.opened_at = time.time()
            logger.warning(f"Circuit breaker for {self.service} opened ({self.failures} failures)")


# ============================================================================
# Rate Limiting Backends
# ============================================================================

class RateLimitBackend(ABC):
    """Abstract base class for rate limit backends"""
    
    @abstractmethod
    async def check(self, key: str, limit: int, window: int) -> Tuple[bool, Dict[str, Any]]:
        """Check if request is allowed"""
        pass
    
    @abstractmethod
    async def get_state(self, key: str) -> Optional[RateLimitState]:
        """Get current state for a key"""
        pass


class InMemoryRateLimitBackend(RateLimitBackend):
    """In-memory rate limit storage (for single instance)"""
    
    def __init__(self):
        self._states: Dict[str, RateLimitState] = {}
        self._lock = asyncio.Lock()
    
    async def check(self, key: str, limit: int, window: int) -> Tuple[bool, Dict[str, Any]]:
        """Check if request is allowed using sliding window"""
        async with self._lock:
            now = time.time()
            
            # Get or create state
            if key not in self._states:
                self._states[key] = RateLimitState(key=key, window_start=now)
            
            state = self._states[key]
            state.reset_window(window)
            
            # Check if limit exceeded
            if state.requests_in_window >= limit:
                retry_after = int(window - (now - state.window_start)) + 1
                return False, {
                    "limit": limit,
                    "window": window,
                    "current": state.requests_in_window,
                    "retry_after": retry_after,
                }
            
            # Allow request
            state.requests_in_window += 1
            state.last_request = now
            
            return True, {
                "limit": limit,
                "window": window,
                "current": state.requests_in_window,
                "remaining": limit - state.requests_in_window,
            }
    
    async def get_state(self, key: str) -> Optional[RateLimitState]:
        """Get current state for a key"""
        return self._states.get(key)
    
    async def cleanup_expired(self, max_age: int = 3600):
        """Clean up expired entries"""
        now = time.time()
        async with self._lock:
            expired = [
                k for k, v in self._states.items()
                if now - v.last_request > max_age
            ]
            for k in expired:
                del self._states[k]


class TokenBucketBackend(RateLimitBackend):
    """Token bucket rate limiting algorithm"""
    
    def __init__(self):
        self._buckets: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
    
    async def check(self, key: str, limit: int, window: int) -> Tuple[bool, Dict[str, Any]]:
        """Check using token bucket"""
        async with self._lock:
            now = time.time()
            
            # Get or create bucket
            if key not in self._buckets:
                self._buckets[key] = {
                    "tokens": limit,
                    "last_update": now,
                }
            
            bucket = self._buckets[key]
            
            # Add tokens based on time passed
            time_passed = now - bucket["last_update"]
            tokens_to_add = time_passed * (limit / window)
            bucket["tokens"] = min(limit, bucket["tokens"] + tokens_to_add)
            bucket["last_update"] = now
            
            # Check if we have tokens
            if bucket["tokens"] < 1:
                retry_after = int((1 - bucket["tokens"]) / (limit / window)) + 1
                return False, {
                    "limit": limit,
                    "window": window,
                    "current": int(limit - bucket["tokens"]),
                    "retry_after": retry_after,
                }
            
            # Consume token
            bucket["tokens"] -= 1
            
            return True, {
                "limit": limit,
                "window": window,
                "current": int(limit - bucket["tokens"]),
                "remaining": int(bucket["tokens"]),
            }
    
    async def get_state(self, key: str) -> Optional[RateLimitState]:
        """Get bucket state"""
        bucket = self._buckets.get(key)
        if bucket:
            return RateLimitState(
                key=key,
                tokens=bucket["tokens"],
                last_request=bucket["last_update"],
            )
        return None


# ============================================================================
# Rate Limiter
# ============================================================================

class RateLimiter:
    """Production rate limiter with multiple strategies"""
    
    def __init__(
        self,
        backend: Optional[RateLimitBackend] = None,
        config: Optional[RateLimitConfig] = None,
    ):
        self.backend = backend or TokenBucketBackend()
        self.config = config or RateLimitConfig()
        self._concurrent_semaphores: Dict[str, asyncio.Semaphore] = {}
        self._global_semaphore = asyncio.Semaphore(self.config.max_concurrent_global)
        self._lock = asyncio.Lock()
    
    def _make_key(
        self,
        identifier: str,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
    ) -> str:
        """Create a rate limit key"""
        parts = [identifier]
        if endpoint:
            parts.append(endpoint)
        if method:
            parts.append(method)
        return hashlib.sha256(":".join(parts).encode()).hexdigest()[:16]
    
    async def check_rate_limit(
        self,
        identifier: str,
        limit_type: str = "per_minute",
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check if request is within rate limit"""
        key = self._make_key(identifier, endpoint, method)
        
        # Get limit based on type
        if limit_type == "per_minute":
            limit = self.config.requests_per_minute
            window = 60
        elif limit_type == "per_hour":
            limit = self.config.requests_per_hour
            window = 3600
        elif limit_type == "per_day":
            limit = self.config.requests_per_day
            window = 86400
        else:
            limit = self.config.requests_per_minute
            window = 60
        
        # Apply adaptive reduction if enabled and under high load
        if self.config.enable_adaptive:
            current_load = self._get_current_load()
            if current_load > self.config.high_load_threshold:
                limit = int(limit * self.config.adaptive_reduction_factor)
        
        return await self.backend.check(key, limit, window)
    
    def _get_current_load(self) -> float:
        """Get current system load (0.0 - 1.0)"""
        # Simple implementation - can be enhanced with actual system metrics
        return 1.0 - (self._global_semaphore._value / self.config.max_concurrent_global)
    
    async def acquire_concurrent(self, identifier: str) -> bool:
        """Acquire a concurrent request slot"""
        # Check global limit
        if self._global_semaphore.locked():
            raise ConcurrencyLimitExceeded("Server at global capacity")
        
        # Check per-user limit
        async with self._lock:
            if identifier not in self._concurrent_semaphores:
                self._concurrent_semaphores[identifier] = asyncio.Semaphore(
                    self.config.max_concurrent_per_user
                )
        
        user_semaphore = self._concurrent_semaphores[identifier]
        
        if user_semaphore.locked():
            raise ConcurrencyLimitExceeded("Too many concurrent requests for user")
        
        # Acquire both semaphores
        await self._global_semaphore.acquire()
        await user_semaphore.acquire()
        
        return True
    
    async def release_concurrent(self, identifier: str):
        """Release a concurrent request slot"""
        self._global_semaphore.release()
        
        async with self._lock:
            if identifier in self._concurrent_semaphores:
                self._concurrent_semaphores[identifier].release()


# ============================================================================
# Circuit Breaker
# ============================================================================

class CircuitBreaker:
    """Circuit breaker pattern for external services"""
    
    def __init__(
        self,
        service_name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_max_calls: int = 3,
    ):
        self.service_name = service_name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self._state = CircuitBreakerState(service=service_name)
        self._lock = asyncio.Lock()
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Call a function with circuit breaker protection"""
        async with self._lock:
            # Check if circuit is open
            if self._state.state == "open":
                # Check if we should try half-open
                if self._state.opened_at:
                    elapsed = time.time() - self._state.opened_at
                    if elapsed < self.recovery_timeout:
                        retry_after = int(self.recovery_timeout - elapsed)
                        raise CircuitBreakerOpen(
                            self.service_name,
                            retry_after=retry_after,
                        )
                    else:
                        # Try half-open
                        self._state.state = "half_open"
                        self._state.success_count = 0
                        logger.info(f"Circuit breaker for {self.service_name} half-opened")
                else:
                    raise CircuitBreakerOpen(self.service_name)
        
        # Execute the call
        try:
            result = await func(*args, **kwargs)
            await self._record_success()
            return result
        except Exception as e:
            await self._record_failure()
            raise
    
    async def _record_success(self):
        """Record a successful call"""
        async with self._lock:
            self._state.record_success()
    
    async def _record_failure(self):
        """Record a failed call"""
        async with self._lock:
            self._state.record_failure()
    
    @property
    def current_state(self) -> str:
        """Get current circuit state"""
        return self._state.state
    
    async def reset(self):
        """Manually reset the circuit breaker"""
        async with self._lock:
            self._state = CircuitBreakerState(service=self.service_name)


# ============================================================================
# Decorators
# ============================================================================

def rate_limit(
    requests_per_minute: int = 60,
    requests_per_hour: Optional[int] = None,
    key_func: Optional[Callable] = None,
):
    """Decorator to apply rate limiting to an endpoint"""
    def decorator(func: Callable) -> Callable:
        limiter = RateLimiter()
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Get identifier
            if key_func:
                identifier = key_func(*args, **kwargs)
            else:
                # Try to extract from request
                request = kwargs.get('request') or (args[0] if args else None)
                identifier = getattr(request, 'client', None)
                if identifier:
                    identifier = getattr(identifier, 'host', 'unknown')
                else:
                    identifier = 'unknown'
            
            # Check rate limit
            allowed, info = await limiter.check_rate_limit(
                identifier,
                limit_type="per_minute",
            )
            
            if not allowed:
                raise RateLimitExceeded(
                    retry_after=info.get("retry_after"),
                    limit=info.get("limit"),
                    window=info.get("window"),
                )
            
            return await func(*args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return func
    
    return decorator


def circuit_breaker(
    service_name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
):
    """Decorator to apply circuit breaker pattern"""
    def decorator(func: Callable) -> Callable:
        breaker = CircuitBreaker(
            service_name=service_name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
        )
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await breaker.call(func, *args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return func
    
    return decorator


def concurrent_limit(max_concurrent: int = 10, key_func: Optional[Callable] = None):
    """Decorator to limit concurrent executions"""
    def decorator(func: Callable) -> Callable:
        semaphores: Dict[str, asyncio.Semaphore] = {}
        lock = asyncio.Lock()
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Get key
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                key = "global"
            
            # Get or create semaphore
            async with lock:
                if key not in semaphores:
                    semaphores[key] = asyncio.Semaphore(max_concurrent)
            
            semaphore = semaphores[key]
            
            if semaphore.locked():
                raise ConcurrencyLimitExceeded()
            
            async with semaphore:
                return await func(*args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return func
    
    return decorator


# ============================================================================
# Global Instances
# ============================================================================

# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None
# Circuit breakers for external services
_circuit_breakers: Dict[str, CircuitBreaker] = {}


def get_rate_limiter() -> RateLimiter:
    """Get or create global rate limiter"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def get_circuit_breaker(service_name: str) -> CircuitBreaker:
    """Get or create circuit breaker for a service"""
    global _circuit_breakers
    if service_name not in _circuit_breakers:
        _circuit_breakers[service_name] = CircuitBreaker(service_name=service_name)
    return _circuit_breakers[service_name]


# ============================================================================
# Service-Specific Circuit Breakers
# ============================================================================

async def call_with_circuit_breaker(
    service_name: str,
    func: Callable,
    *args,
    **kwargs
) -> Any:
    """Call a function with circuit breaker protection"""
    breaker = get_circuit_breaker(service_name)
    return await breaker.call(func, *args, **kwargs)


# Convenience functions for specific services
async def call_ollama_with_circuit_breaker(func: Callable, *args, **kwargs) -> Any:
    """Call Ollama with circuit breaker protection"""
    return await call_with_circuit_breaker("ollama", func, *args, **kwargs)


async def call_signal_with_circuit_breaker(func: Callable, *args, **kwargs) -> Any:
    """Call Signal with circuit breaker protection"""
    return await call_with_circuit_breaker("signal", func, *args, **kwargs)


async def call_brave_with_circuit_breaker(func: Callable, *args, **kwargs) -> Any:
    """Call Brave Search with circuit breaker protection"""
    return await call_with_circuit_breaker("brave", func, *args, **kwargs)


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    # Exceptions
    'RateLimitExceeded',
    'CircuitBreakerOpen',
    'ConcurrencyLimitExceeded',
    # Classes
    'RateLimitConfig',
    'RateLimitState',
    'CircuitBreakerState',
    'RateLimitBackend',
    'InMemoryRateLimitBackend',
    'TokenBucketBackend',
    'RateLimiter',
    'CircuitBreaker',
    # Functions
    'get_rate_limiter',
    'get_circuit_breaker',
    'call_with_circuit_breaker',
    'call_ollama_with_circuit_breaker',
    'call_signal_with_circuit_breaker',
    'call_brave_with_circuit_breaker',
    # Decorators
    'rate_limit',
    'circuit_breaker',
    'concurrent_limit',
]
