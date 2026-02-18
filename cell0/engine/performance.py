"""
Performance Optimizations for Cell 0 OS

Production-grade performance enhancements:
- Connection pooling for external services
- Async optimizations
- Request coalescing for duplicate queries
- Batch processing utilities
- Rate limiting with token bucket
- Memory-efficient data structures

Author: KULLU (Cell 0 OS)
"""

import asyncio
import hashlib
import logging
import time
from typing import Any, Dict, Optional, List, Callable, TypeVar, Generic, Set
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict
import functools
import weakref
from contextlib import asynccontextmanager
import aiohttp
import aiohttp.client

logger = logging.getLogger("cell0.engine.performance")

T = TypeVar('T')


class ConnectionPool:
    """
    Generic connection pool for external services
    
    Manages a pool of connections with:
    - Min/max pool size
    - Connection health checks
    - Automatic reconnection
    - Connection timeouts
    """
    
    def __init__(
        self,
        factory: Callable[[], Any],
        min_size: int = 2,
        max_size: int = 10,
        max_idle_time: float = 300,
        health_check_interval: float = 60,
    ):
        self.factory = factory
        self.min_size = min_size
        self.max_size = max_size
        self.max_idle_time = max_idle_time
        self.health_check_interval = health_check_interval
        
        self._available: List[Any] = []
        self._in_use: Set[Any] = set()
        self._lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(max_size)
        self._connection_times: Dict[Any, datetime] = {}
        self._running = False
        self._health_check_task: Optional[asyncio.Task] = None
        
    async def start(self):
        """Initialize the pool with minimum connections"""
        async with self._lock:
            for _ in range(self.min_size):
                try:
                    conn = await self._create_connection()
                    self._available.append(conn)
                except Exception as e:
                    logger.error(f"Failed to create initial connection: {e}")
                    
        self._running = True
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info(f"Connection pool started with {len(self._available)} connections")
        
    async def stop(self):
        """Close all connections and stop the pool"""
        self._running = False
        
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
                
        async with self._lock:
            for conn in list(self._available) + list(self._in_use):
                try:
                    await self._close_connection(conn)
                except Exception as e:
                    logger.warning(f"Error closing connection: {e}")
                    
            self._available.clear()
            self._in_use.clear()
            
        logger.info("Connection pool stopped")
        
    async def _create_connection(self) -> Any:
        """Create a new connection"""
        conn = await self.factory()
        self._connection_times[conn] = datetime.utcnow()
        return conn
        
    async def _close_connection(self, conn: Any):
        """Close a connection"""
        self._connection_times.pop(conn, None)
        if hasattr(conn, 'close'):
            await conn.close()
        elif hasattr(conn, 'disconnect'):
            await conn.disconnect()
            
    async def _is_healthy(self, conn: Any) -> bool:
        """Check if a connection is healthy"""
        if hasattr(conn, 'ping'):
            try:
                await conn.ping()
                return True
            except Exception:
                return False
        return True
        
    async def _health_check_loop(self):
        """Periodic health checks"""
        while self._running:
            try:
                await asyncio.sleep(self.health_check_interval)
                
                async with self._lock:
                    # Check available connections
                    healthy = []
                    for conn in self._available:
                        if await self._is_healthy(conn):
                            # Check idle time
                            idle_time = (datetime.utcnow() - self._connection_times[conn]).total_seconds()
                            if idle_time < self.max_idle_time or len(healthy) < self.min_size:
                                healthy.append(conn)
                            else:
                                await self._close_connection(conn)
                        else:
                            await self._close_connection(conn)
                            
                    self._available = healthy
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                
    @asynccontextmanager
    async def acquire(self, timeout: float = 30.0):
        """Acquire a connection from the pool"""
        conn = None
        
        try:
            async with self._semaphore:
                async with self._lock:
                    if self._available:
                        conn = self._available.pop()
                    else:
                        conn = await self._create_connection()
                        
                    self._in_use.add(conn)
                    self._connection_times[conn] = datetime.utcnow()
                    
                yield conn
                
        finally:
            if conn:
                async with self._lock:
                    self._in_use.discard(conn)
                    if len(self._available) < self.max_size:
                        self._available.append(conn)
                    else:
                        await self._close_connection(conn)


class HTTPConnectionPool:
    """
    Managed HTTP connection pool using aiohttp
    
    Provides:
    - Persistent connections
    - Connection reuse
    - Timeout management
    - Automatic retries
    """
    
    def __init__(
        self,
        base_url: str,
        max_connections: int = 100,
        max_connections_per_host: int = 10,
        timeout: float = 30.0,
        keepalive_timeout: float = 60.0,
    ):
        self.base_url = base_url.rstrip('/')
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        
        connector = aiohttp.TCPConnector(
            limit=max_connections,
            limit_per_host=max_connections_per_host,
            keepalive_timeout=keepalive_timeout,
            enable_cleanup_closed=True,
            force_close=False,
        )
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=self.timeout,
            headers={
                "User-Agent": "Cell0-OS/1.0",
                "Accept": "application/json",
            },
        )
        
    async def close(self):
        """Close the session"""
        await self.session.close()
        
    async def get(
        self,
        path: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        **kwargs,
    ) -> aiohttp.ClientResponse:
        """Make GET request"""
        url = f"{self.base_url}{path}"
        return await self.session.get(url, params=params, headers=headers, **kwargs)
        
    async def post(
        self,
        path: str,
        json_data: Optional[Dict] = None,
        data: Optional[Any] = None,
        headers: Optional[Dict] = None,
        **kwargs,
    ) -> aiohttp.ClientResponse:
        """Make POST request"""
        url = f"{self.base_url}{path}"
        return await self.session.post(
            url, json=json_data, data=data, headers=headers, **kwargs
        )
        
    async def put(
        self,
        path: str,
        json_data: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        **kwargs,
    ) -> aiohttp.ClientResponse:
        """Make PUT request"""
        url = f"{self.base_url}{path}"
        return await self.session.put(url, json=json_data, headers=headers, **kwargs)
        
    async def delete(
        self,
        path: str,
        headers: Optional[Dict] = None,
        **kwargs,
    ) -> aiohttp.ClientResponse:
        """Make DELETE request"""
        url = f"{self.base_url}{path}"
        return await self.session.delete(url, headers=headers, **kwargs)


class RequestCoalescer:
    """
    Request coalescing for duplicate queries
    
    When multiple identical requests are made simultaneously,
    only one is executed and all waiters receive the result.
    
    This prevents thundering herd problems and reduces load.
    """
    
    def __init__(self, default_ttl: float = 1.0):
        self.default_ttl = default_ttl
        self._inflight: Dict[str, asyncio.Future] = {}
        self._lock = asyncio.Lock()
        self._stats = {
            "coalesced": 0,
            "executed": 0,
        }
        
    def _generate_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """Generate unique key for request"""
        key_data = f"{func_name}:{args}:{sorted(kwargs.items())}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:16]
        
    async def coalesce(
        self,
        key: str,
        fn: Callable[..., asyncio.Future],
        *args,
        **kwargs,
    ) -> Any:
        """
        Execute function with request coalescing
        
        Args:
            key: Unique key for this request
            fn: Async function to execute
            *args: Arguments to fn
            **kwargs: Keyword arguments to fn
            
        Returns:
            Result from fn
        """
        async with self._lock:
            # Check if request is already in flight
            if key in self._inflight:
                future = self._inflight[key]
                self._stats["coalesced"] += 1
                logger.debug(f"Coalescing request for key: {key}")
                return await future
                
            # Create future for this request
            future = asyncio.Future()
            self._inflight[key] = future
            self._stats["executed"] += 1
            
        try:
            # Execute the function
            result = await fn(*args, **kwargs)
            future.set_result(result)
            return result
            
        except Exception as e:
            future.set_exception(e)
            raise
            
        finally:
            # Remove from in-flight
            async with self._lock:
                self._inflight.pop(key, None)
                
    def get_stats(self) -> Dict[str, int]:
        """Get coalescer statistics"""
        return dict(self._stats)


def coalesced(coalescer: Optional[RequestCoalescer] = None):
    """
    Decorator for request coalescing
    
    Usage:
        coalescer = RequestCoalescer()
        
        @coalesced(coalescer)
        async def expensive_operation(param: str):
            return await fetch_data(param)
    """
    coal = coalescer or RequestCoalescer()
    
    def decorator(fn):
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            # Generate key from function name and arguments
            func_name = fn.__name__
            key = f"{func_name}:{hash((args, tuple(sorted(kwargs.items()))))}"
            
            return await coal.coalesce(key, fn, *args, **kwargs)
            
        return wrapper
    return decorator


class AsyncBatchProcessor(Generic[T]):
    """
    Batch processor for async operations
    
    Collects items and processes them in batches for efficiency.
    Useful for database writes, API calls, etc.
    """
    
    def __init__(
        self,
        processor: Callable[[List[T]], asyncio.Future],
        batch_size: int = 100,
        max_wait_time: float = 1.0,
    ):
        self.processor = processor
        self.batch_size = batch_size
        self.max_wait_time = max_wait_time
        
        self._buffer: List[T] = []
        self._lock = asyncio.Lock()
        self._flush_event = asyncio.Event()
        self._flush_task: Optional[asyncio.Task] = None
        self._running = False
        self._stats = {
            "batches_processed": 0,
            "items_processed": 0,
        }
        
    async def start(self):
        """Start the batch processor"""
        self._running = True
        self._flush_task = asyncio.create_task(self._flush_loop())
        
    async def stop(self):
        """Stop the batch processor"""
        self._running = False
        
        # Final flush
        await self.flush()
        
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
                
    async def add(self, item: T) -> None:
        """Add an item to the batch"""
        async with self._lock:
            self._buffer.append(item)
            
            if len(self._buffer) >= self.batch_size:
                self._flush_event.set()
                
    async def add_many(self, items: List[T]) -> None:
        """Add multiple items to the batch"""
        async with self._lock:
            self._buffer.extend(items)
            
            if len(self._buffer) >= self.batch_size:
                self._flush_event.set()
                
    async def _flush_loop(self):
        """Background flush loop"""
        while self._running:
            try:
                # Wait for flush signal or timeout
                await asyncio.wait_for(
                    self._flush_event.wait(),
                    timeout=self.max_wait_time,
                )
            except asyncio.TimeoutError:
                pass
                
            if self._buffer:
                await self.flush()
                
            self._flush_event.clear()
            
    async def flush(self) -> int:
        """Flush the current batch"""
        async with self._lock:
            if not self._buffer:
                return 0
                
            batch = self._buffer[:]
            self._buffer.clear()
            
        try:
            await self.processor(batch)
            self._stats["batches_processed"] += 1
            self._stats["items_processed"] += len(batch)
            return len(batch)
            
        except Exception as e:
            logger.error(f"Batch processing error: {e}")
            # Re-add items to buffer for retry
            async with self._lock:
                self._buffer.extend(batch)
            return 0
            
    def get_stats(self) -> Dict[str, int]:
        """Get batch processor statistics"""
        return dict(self._stats)


class TokenBucketRateLimiter:
    """
    Token bucket rate limiter
    
    Provides smooth rate limiting with burst capability.
    """
    
    def __init__(
        self,
        rate: float,  # tokens per second
        capacity: int,  # maximum bucket size
    ):
        self.rate = rate
        self.capacity = capacity
        self._tokens = capacity
        self._last_update = time.monotonic()
        self._lock = asyncio.Lock()
        
    async def acquire(self, tokens: int = 1, timeout: Optional[float] = None) -> bool:
        """
        Acquire tokens from the bucket
        
        Args:
            tokens: Number of tokens to acquire
            timeout: Maximum time to wait
            
        Returns:
            True if tokens were acquired
        """
        start_time = time.monotonic()
        
        while True:
            async with self._lock:
                self._add_tokens()
                
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return True
                    
                if timeout is not None:
                    wait_time = (tokens - self._tokens) / self.rate
                    if time.monotonic() - start_time + wait_time > timeout:
                        return False
                        
            # Wait a bit before retrying
            await asyncio.sleep(0.01)
            
    def _add_tokens(self):
        """Add tokens based on elapsed time"""
        now = time.monotonic()
        elapsed = now - self._last_update
        self._last_update = now
        
        self._tokens = min(
            self.capacity,
            self._tokens + elapsed * self.rate
        )
        
    async def __aenter__(self):
        await self.acquire()
        return self
        
    async def __aexit__(self, *args):
        pass


class Memoizer:
    """
    Async-aware memoization with TTL
    
    Caches function results with time-based expiration.
    """
    
    def __init__(self, maxsize: int = 128, ttl: float = 300):
        self.maxsize = maxsize
        self.ttl = ttl
        self._cache: Dict[str, Any] = {}
        self._timestamps: Dict[str, float] = {}
        self._lock = asyncio.Lock()
        
    def _generate_key(self, args: tuple, kwargs: dict) -> str:
        """Generate cache key"""
        key_data = f"{args}:{sorted(kwargs.items())}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:16]
        
    async def get_or_compute(
        self,
        fn: Callable[..., asyncio.Future],
        args: tuple,
        kwargs: dict,
    ) -> Any:
        """Get cached result or compute and cache"""
        key = self._generate_key(args, kwargs)
        
        async with self._lock:
            # Check if cached and not expired
            if key in self._cache:
                timestamp = self._timestamps.get(key, 0)
                if time.monotonic() - timestamp < self.ttl:
                    return self._cache[key]
                    
        # Compute
        result = await fn(*args, **kwargs)
        
        # Cache result
        async with self._lock:
            # Evict oldest if at capacity
            if len(self._cache) >= self.maxsize:
                oldest_key = min(self._timestamps, key=self._timestamps.get)
                del self._cache[oldest_key]
                del self._timestamps[oldest_key]
                
            self._cache[key] = result
            self._timestamps[key] = time.monotonic()
            
        return result


def async_lru_cache(maxsize: int = 128, ttl: float = 300):
    """
    LRU cache decorator for async functions
    
    Usage:
        @async_lru_cache(maxsize=100, ttl=600)
        async def expensive_function(arg):
            return await compute(arg)
    """
    memoizer = Memoizer(maxsize=maxsize, ttl=ttl)
    
    def decorator(fn):
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            return await memoizer.get_or_compute(fn, args, kwargs)
        return wrapper
    return decorator


class LazyLoader:
    """
    Lazy loading wrapper for expensive resources
    
    Delays initialization until first access.
    """
    
    def __init__(self, factory: Callable[[], Any]):
        self.factory = factory
        self._instance: Optional[Any] = None
        self._lock = asyncio.Lock()
        
    async def get(self) -> Any:
        """Get the lazy-loaded instance"""
        if self._instance is None:
            async with self._lock:
                if self._instance is None:
                    result = self.factory()
                    if asyncio.iscoroutine(result):
                        self._instance = await result
                    else:
                        self._instance = result
        return self._instance


# Global instances
_global_http_pools: Dict[str, HTTPConnectionPool] = {}
_global_coalescer = RequestCoalescer()


def get_http_pool(base_url: str, **kwargs) -> HTTPConnectionPool:
    """Get or create HTTP connection pool for base URL"""
    if base_url not in _global_http_pools:
        _global_http_pools[base_url] = HTTPConnectionPool(base_url, **kwargs)
    return _global_http_pools[base_url]


async def close_all_http_pools():
    """Close all HTTP connection pools"""
    for pool in _global_http_pools.values():
        await pool.close()
    _global_http_pools.clear()


def get_request_coalescer() -> RequestCoalescer:
    """Get global request coalescer"""
    return _global_coalescer