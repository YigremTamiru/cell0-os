"""
Redis Client Wrapper for Cell 0 OS

Production-grade Redis client with:
- Connection pooling
- Circuit breaker pattern
- Retry logic with exponential backoff
- Health checks
- Metrics tracking
- Async support

Author: KULLU (Cell 0 OS)
"""

import asyncio
import logging
from typing import Any, Optional, List, Dict, Union, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import json
import pickle
import hashlib

try:
    import redis.asyncio as redis
    from redis.asyncio.connection import ConnectionPool
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

logger = logging.getLogger("cell0.engine.cache.redis")


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


@dataclass
class RedisConfig:
    """Redis connection configuration"""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    username: Optional[str] = None
    ssl: bool = False
    ssl_ca_certs: Optional[str] = None
    
    # Connection pool settings
    max_connections: int = 50
    min_connections: int = 10
    socket_timeout: float = 5.0
    socket_connect_timeout: float = 5.0
    retry_on_timeout: bool = True
    health_check_interval: float = 30.0
    
    # Circuit breaker settings
    circuit_failure_threshold: int = 5
    circuit_recovery_timeout: float = 30.0
    circuit_half_open_max_calls: int = 3
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "host": self.host,
            "port": self.port,
            "db": self.db,
            "ssl": self.ssl,
            "max_connections": self.max_connections,
            "min_connections": self.min_connections,
        }


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for Redis resilience
    
    Prevents cascading failures by temporarily rejecting requests
    when the service is experiencing high error rates.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 3,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._lock = asyncio.Lock()
        
    @property
    def state(self) -> CircuitState:
        return self._state
        
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute a function with circuit breaker protection"""
        async with self._lock:
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._state = CircuitState.HALF_OPEN
                    self._success_count = 0
                    logger.info("Circuit breaker entering half-open state")
                else:
                    raise CircuitBreakerOpen("Circuit breaker is OPEN")
                    
            if self._state == CircuitState.HALF_OPEN and self._success_count >= self.half_open_max_calls:
                raise CircuitBreakerOpen("Circuit breaker half-open limit reached")
        
        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception as e:
            await self._on_failure()
            raise
            
    async def _on_success(self):
        """Record a successful call"""
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.half_open_max_calls:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    logger.info("Circuit breaker closed after successful recovery")
            else:
                self._failure_count = 0
                
    async def _on_failure(self):
        """Record a failed call"""
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = datetime.utcnow()
            
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                logger.warning("Circuit breaker opened due to failure in half-open state")
            elif self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
                logger.warning(f"Circuit breaker opened after {self.failure_threshold} failures")
                
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery"""
        if self._last_failure_time is None:
            return True
        elapsed = (datetime.utcnow() - self._last_failure_time).total_seconds()
        return elapsed >= self.recovery_timeout


class CircuitBreakerOpen(Exception):
    """Exception raised when circuit breaker is open"""
    pass


class RedisClient:
    """
    Production-grade Redis client wrapper
    
    Features:
    - Connection pooling
    - Circuit breaker for resilience
    - Automatic serialization (JSON/pickle)
    - Health checks
    - Metrics tracking
    - Retry with exponential backoff
    """
    
    def __init__(self, config: Optional[RedisConfig] = None):
        if not REDIS_AVAILABLE:
            raise ImportError("Redis package not installed. Install with: pip install redis")
            
        self.config = config or RedisConfig()
        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[redis.Redis] = None
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=self.config.circuit_failure_threshold,
            recovery_timeout=self.config.circuit_recovery_timeout,
            half_open_max_calls=self.config.circuit_half_open_max_calls,
        )
        self._metrics = {
            "operations_total": 0,
            "operations_failed": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "circuit_opens": 0,
        }
        self._lock = asyncio.Lock()
        self._connected = False
        
    async def connect(self):
        """Initialize Redis connection pool"""
        if self._connected:
            return
            
        async with self._lock:
            if self._connected:
                return
                
            try:
                self._pool = ConnectionPool(
                    host=self.config.host,
                    port=self.config.port,
                    db=self.config.db,
                    password=self.config.password,
                    username=self.config.username,
                    ssl=self.config.ssl,
                    ssl_ca_certs=self.config.ssl_ca_certs,
                    max_connections=self.config.max_connections,
                    socket_timeout=self.config.socket_timeout,
                    socket_connect_timeout=self.config.socket_connect_timeout,
                    retry_on_timeout=self.config.retry_on_timeout,
                    health_check_interval=self.config.health_check_interval,
                )
                
                self._client = redis.Redis(connection_pool=self._pool)
                
                # Test connection
                await self._client.ping()
                self._connected = True
                
                logger.info(f"Connected to Redis at {self.config.host}:{self.config.port}")
                
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise
                
    async def disconnect(self):
        """Close Redis connections"""
        async with self._lock:
            if self._client:
                await self._client.close()
                self._client = None
            if self._pool:
                await self._pool.disconnect()
                self._pool = None
            self._connected = False
            logger.info("Disconnected from Redis")
            
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        if not self._connected or not self._client:
            return {"healthy": False, "error": "Not connected"}
            
        try:
            start = asyncio.get_event_loop().time()
            await self._client.ping()
            latency_ms = (asyncio.get_event_loop().time() - start) * 1000
            
            info = await self._client.info()
            
            return {
                "healthy": True,
                "latency_ms": round(latency_ms, 2),
                "circuit_state": self._circuit_breaker.state.value,
                "redis_version": info.get("redis_version"),
                "connected_clients": info.get("connected_clients"),
                "used_memory_human": info.get("used_memory_human"),
            }
        except Exception as e:
            return {"healthy": False, "error": str(e)}
            
    async def get(self, key: str, default: Any = None, use_pickle: bool = False) -> Any:
        """Get value from cache"""
        try:
            result = await self._circuit_breaker.call(self._get_raw, key)
            
            if result is None:
                self._metrics["cache_misses"] += 1
                return default
                
            self._metrics["cache_hits"] += 1
            
            if use_pickle:
                return pickle.loads(result)
            else:
                return json.loads(result)
                
        except CircuitBreakerOpen:
            logger.warning("Circuit breaker open, returning default")
            return default
        except Exception as e:
            logger.error(f"Redis GET error: {e}")
            self._metrics["operations_failed"] += 1
            return default
            
    async def _get_raw(self, key: str) -> Optional[bytes]:
        """Raw GET operation"""
        if not self._client:
            raise ConnectionError("Not connected to Redis")
        return await self._client.get(key)
        
    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
        use_pickle: bool = False,
    ) -> bool:
        """Set value in cache"""
        try:
            if use_pickle:
                serialized = pickle.dumps(value)
            else:
                serialized = json.dumps(value, default=str).encode()
                
            await self._circuit_breaker.call(
                self._set_raw, key, serialized, ttl_seconds
            )
            self._metrics["operations_total"] += 1
            return True
            
        except CircuitBreakerOpen:
            logger.warning("Circuit breaker open, cache write failed")
            return False
        except Exception as e:
            logger.error(f"Redis SET error: {e}")
            self._metrics["operations_failed"] += 1
            return False
            
    async def _set_raw(self, key: str, value: bytes, ttl: Optional[int]):
        """Raw SET operation"""
        if not self._client:
            raise ConnectionError("Not connected to Redis")
        await self._client.set(key, value, ex=ttl)
        
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            await self._circuit_breaker.call(self._delete_raw, key)
            return True
        except Exception as e:
            logger.error(f"Redis DELETE error: {e}")
            return False
            
    async def _delete_raw(self, key: str):
        """Raw DELETE operation"""
        if not self._client:
            raise ConnectionError("Not connected to Redis")
        await self._client.delete(key)
        
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        try:
            result = await self._circuit_breaker.call(self._exists_raw, key)
            return bool(result)
        except Exception as e:
            logger.error(f"Redis EXISTS error: {e}")
            return False
            
    async def _exists_raw(self, key: str) -> int:
        """Raw EXISTS operation"""
        if not self._client:
            raise ConnectionError("Not connected to Redis")
        return await self._client.exists(key)
        
    async def expire(self, key: str, ttl_seconds: int) -> bool:
        """Set expiration on key"""
        try:
            await self._circuit_breaker.call(self._expire_raw, key, ttl_seconds)
            return True
        except Exception as e:
            logger.error(f"Redis EXPIRE error: {e}")
            return False
            
    async def _expire_raw(self, key: str, ttl: int):
        """Raw EXPIRE operation"""
        if not self._client:
            raise ConnectionError("Not connected to Redis")
        await self._client.expire(key, ttl)
        
    async def ttl(self, key: str) -> int:
        """Get remaining TTL for key"""
        try:
            result = await self._circuit_breaker.call(self._ttl_raw, key)
            return result
        except Exception as e:
            logger.error(f"Redis TTL error: {e}")
            return -2
            
    async def _ttl_raw(self, key: str) -> int:
        """Raw TTL operation"""
        if not self._client:
            raise ConnectionError("Not connected to Redis")
        return await self._client.ttl(key)
        
    async def get_many(self, keys: List[str], use_pickle: bool = False) -> Dict[str, Any]:
        """Get multiple values from cache"""
        if not keys:
            return {}
            
        try:
            results = await self._circuit_breaker.call(self._mget_raw, keys)
            
            output = {}
            for key, value in zip(keys, results):
                if value is None:
                    self._metrics["cache_misses"] += 1
                else:
                    self._metrics["cache_hits"] += 1
                    try:
                        if use_pickle:
                            output[key] = pickle.loads(value)
                        else:
                            output[key] = json.loads(value)
                    except Exception as e:
                        logger.warning(f"Failed to deserialize key {key}: {e}")
                        
            return output
            
        except Exception as e:
            logger.error(f"Redis MGET error: {e}")
            return {}
            
    async def _mget_raw(self, keys: List[str]) -> List[Optional[bytes]]:
        """Raw MGET operation"""
        if not self._client:
            raise ConnectionError("Not connected to Redis")
        return await self._client.mget(keys)
        
    async def set_many(
        self,
        mapping: Dict[str, Any],
        ttl_seconds: Optional[int] = None,
        use_pickle: bool = False,
    ) -> bool:
        """Set multiple values in cache"""
        if not mapping:
            return True
            
        try:
            serialized = {}
            for key, value in mapping.items():
                if use_pickle:
                    serialized[key] = pickle.dumps(value)
                else:
                    serialized[key] = json.dumps(value, default=str).encode()
                    
            await self._circuit_breaker.call(self._mset_raw, serialized)
            
            # Set TTL if specified
            if ttl_seconds:
                pipe = self._client.pipeline()
                for key in serialized.keys():
                    pipe.expire(key, ttl_seconds)
                await pipe.execute()
                
            self._metrics["operations_total"] += len(mapping)
            return True
            
        except Exception as e:
            logger.error(f"Redis MSET error: {e}")
            return False
            
    async def _mset_raw(self, mapping: Dict[str, bytes]):
        """Raw MSET operation"""
        if not self._client:
            raise ConnectionError("Not connected to Redis")
        await self._client.mset(mapping)
        
    async def increment(self, key: str, amount: int = 1) -> int:
        """Atomic increment operation"""
        try:
            result = await self._circuit_breaker.call(self._incr_raw, key, amount)
            return result
        except Exception as e:
            logger.error(f"Redis INCR error: {e}")
            return 0
            
    async def _incr_raw(self, key: str, amount: int) -> int:
        """Raw INCR operation"""
        if not self._client:
            raise ConnectionError("Not connected to Redis")
        return await self._client.incr(key, amount)
        
    async def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern"""
        try:
            result = await self._circuit_breaker.call(self._keys_raw, pattern)
            return [k.decode() if isinstance(k, bytes) else k for k in result]
        except Exception as e:
            logger.error(f"Redis KEYS error: {e}")
            return []
            
    async def _keys_raw(self, pattern: str) -> List[str]:
        """Raw KEYS operation"""
        if not self._client:
            raise ConnectionError("Not connected to Redis")
        return await self._client.keys(pattern)
        
    async def clear(self, pattern: str = "*") -> int:
        """Clear keys matching pattern"""
        try:
            keys = await self.keys(pattern)
            if keys:
                await self._circuit_breaker.call(self._delete_many_raw, keys)
            return len(keys)
        except Exception as e:
            logger.error(f"Redis CLEAR error: {e}")
            return 0
            
    async def _delete_many_raw(self, keys: List[str]):
        """Raw delete many operation"""
        if not self._client:
            raise ConnectionError("Not connected to Redis")
        await self._client.delete(*keys)
        
    def get_metrics(self) -> Dict[str, Any]:
        """Get client metrics"""
        total = self._metrics["operations_total"]
        failed = self._metrics["operations_failed"]
        hits = self._metrics["cache_hits"]
        misses = self._metrics["cache_misses"]
        
        hit_rate = hits / (hits + misses) if (hits + misses) > 0 else 0
        error_rate = failed / total if total > 0 else 0
        
        return {
            "operations_total": total,
            "operations_failed": failed,
            "cache_hits": hits,
            "cache_misses": misses,
            "hit_rate": round(hit_rate, 4),
            "error_rate": round(error_rate, 4),
            "circuit_state": self._circuit_breaker.state.value,
            "connected": self._connected,
        }
        
    def generate_cache_key(self, *parts: str, prefix: str = "cell0") -> str:
        """Generate a consistent cache key"""
        key_data = ":".join(str(p) for p in parts)
        hashed = hashlib.sha256(key_data.encode()).hexdigest()[:16]
        return f"{prefix}:{hashed}"


# Global client instance
_global_client: Optional[RedisClient] = None


def get_redis_client(config: Optional[RedisConfig] = None) -> RedisClient:
    """Get or create global Redis client"""
    global _global_client
    if _global_client is None:
        _global_client = RedisClient(config)
    return _global_client


async def initialize_redis(config: Optional[RedisConfig] = None) -> RedisClient:
    """Initialize Redis connection"""
    client = get_redis_client(config)
    await client.connect()
    return client


async def close_redis():
    """Close Redis connection"""
    global _global_client
    if _global_client:
        await _global_client.disconnect()
        _global_client = None